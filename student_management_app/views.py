from django.shortcuts import render,HttpResponse, redirect,HttpResponseRedirect
from django.contrib.auth import logout, authenticate, login
from .models import BunkDetection, CustomUser, FaceEncoding, Staffs, Students, AdminHOD
from django.contrib import messages
import cv2
import face_recognition
import numpy as np
import pickle
import base64
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt  # Import csrf_exempt
from .models import FaceEncoding, CustomUser  # Import your models
from django.core.files.uploadedfile import InMemoryUploadedFile
def home(request):
	return render(request, 'home.html')


def contact(request):
	return render(request, 'contact.html')


def loginUser(request):
	return render(request, 'login_page.html')

@csrf_exempt  # Use csrf_exempt for simplicity in this example.  See notes below.
def doLogin(request):
    if request.method == 'POST':
        try:
            print("Login request received")

            # Ensure an image file is received
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image received'}, status=400)

            print(f"Image name: {image_file.name}")
            print(f"Image content type: {image_file.content_type}")

            if isinstance(image_file, InMemoryUploadedFile):
                image_bytes = image_file.read()
            else:
                return JsonResponse({'error': 'Unsupported file type'}, status=400)

            try:
                np_arr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    return JsonResponse({'error': 'Image decoding failed'}, status=400)

                # --- Debugging: Check frame shape and data type ---
                print(f"Frame shape: {frame.shape}")
                print(f"Frame data type: {frame.dtype}")

                # --- Potential Fix: Ensure uint8 data type ---
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                    print("Frame data type converted to uint8")

                # --- Debugging: Save the Decoded Image (Temporarily!) ---
                # cv2.imwrite("debug_decoded_image.jpg", frame)

            except cv2.error as e:
                print(f"OpenCV Error: {e}")
                return JsonResponse({'error': f'Image decoding error: {e}'}, status=400)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # --- Debugging: Check rgb_frame shape and data type ---
            print(f"RGB Frame shape: {rgb_frame.shape}")
            print(f"RGB Frame data type: {rgb_frame.dtype}")

            try:
                face_locations = face_recognition.face_locations(rgb_frame)
                if not face_locations:
                    return JsonResponse({'error': 'No face detected'}, status=400)

                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if not face_encodings:
                    return JsonResponse({'error': 'Face encoding failed'}, status=400)

                face_encoding = face_encodings[0]

            except Exception as e:
                print(f"Face Recognition Error: {e}")
                return JsonResponse({'error': f'Face recognition error: {e}'}, status=400)

            # ... (rest of your code - comparison, login, etc.) ...
            # Compare with stored encodings
            for stored_face in FaceEncoding.objects.all():
                stored_encoding = pickle.loads(stored_face.encoding)
                results = face_recognition.compare_faces([stored_encoding], face_encoding, tolerance=0.5)

                if True in results:
                    print(f"Authenticated: {stored_face.user.username}")

                    # Log the user in
                    login(request, stored_face.user)

                    # Determine redirect URL based on role
                    redirect_url = {
                        CustomUser.STUDENT: 'student_home/',
                        CustomUser.STAFF: 'staff_home/',
                        CustomUser.HOD: 'admin_home/'
                    }.get(stored_face.user.user_type, 'home/')

                    return JsonResponse({'success': True, 'redirect_url': redirect_url})

            # If no match found
            return JsonResponse({'error': 'Face not registered. Please register first.'}, status=401)

        except Exception as e:
            print("Error during login:", str(e))
            return JsonResponse({'error': 'An error occurred during authentication'}, status=500)

    return render(request, 'login_page.html')

	
def registration(request):
	return render(request, 'registration.html')
	
def doRegistration(request):
    if request.method == 'POST':
        try:
            print(request.POST)  # Debugging
            
            # Get form data
            email_id = request.POST.get('email')
            password = request.POST.get('password')
            face_data = request.POST.get('faceData')

            # Validation Checks
            if not (email_id and password and face_data):
                messages.error(request, 'Please provide all the details including face data!')
                return render(request, 'registration.html')

            if CustomUser.objects.filter(email=email_id).exists():
                messages.error(request, 'User with this email already exists. Please proceed to login!')
                return render(request, 'registration.html')

            # Extract user type
            user_type = get_user_type_from_email(email_id)
            if user_type is None:
                messages.error(request, "Invalid email format! Use '<username>.<staff|student|hod>@<college_domain>'")
                return render(request, 'registration.html')

            username = email_id.split('@')[0].split('.')[0]
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken. Please use a different username.')
                return render(request, 'registration.html')

            # Process face data
            face_data = face_data.split(',')[1]
            image_bytes = base64.b64decode(face_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                messages.error(request, 'No face detected')
                return render(request, 'registration.html')

            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if not face_encodings:
                messages.error(request, 'Could not encode face')
                return render(request, 'registration.html')

            # Check for duplicate face
            existing_faces = FaceEncoding.objects.all()
            for face in existing_faces:
                existing_encoding = pickle.loads(face.encoding)
                matches = face_recognition.compare_faces([existing_encoding], face_encodings[0], tolerance=0.1)
                if True in matches:
                    messages.error(request, 'Face already registered! Please use another face or log in.')
                    return render(request, 'registration.html')

            # Create User
            user = CustomUser.objects.create_user(
                username=username, email=email_id, password=password, user_type=user_type
            )
            user.is_face_registered = True
            user.save()

            # Create role-specific entry
            if user_type == CustomUser.STAFF:
                Staffs.objects.create(admin=user)
            elif user_type == CustomUser.STUDENT:
                Students.objects.create(admin=user)
            elif user_type == CustomUser.HOD:
                AdminHOD.objects.create(admin=user)

            # Store Face Encoding
            FaceEncoding.objects.create(user=user, encoding=pickle.dumps(face_encodings[0]))
            print("Registration successful!  Please log in.", user.username)
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')

        except Exception as e:
            print("Error:", e)
            messages.error(request, "An error occurred during registration. Please try again.")
            return render(request, 'registration.html')

    return render(request, 'registration.html')
# def doRegistration(request):
# 	print(request.POST)
# 	email_id = request.POST.get('email')
# 	password = request.POST.get('password')
# 	face_data = request.POST.get('faceData')
# 	print(email_id)
# 	print(password)
# 	if not (email_id and password):
# 		messages.error(request, 'Please provide all the details!!')
# 		return render(request, 'registration.html')
	
# 	is_user_exists = CustomUser.objects.filter(email=email_id).exists()
# 	if FaceEncoding.objects.filter(encoding=face_data).exists():
# 		messages.error(request, 'This face is already registered. Please use another face or login.')
# 		return render(request, 'registration.html')
# 	if is_user_exists:
# 		messages.error(request, 'User with this email id already exists. Please proceed to login!!')
# 		return render(request, 'registration.html')

# 	user_type = get_user_type_from_email(email_id)

# 	if user_type is None:
# 		messages.error(request, "Please use valid format for the email id: '<username>.<staff|student|hod>@<college_domain>'")
# 		return render(request, 'registration.html')

# 	username = email_id.split('@')[0].split('.')[0]

# 	if CustomUser.objects.filter(username=username).exists():
# 		messages.error(request, 'User with this username already exists. Please use different username')
# 		return render(request, 'registration.html')
# 	face_data = face_data.split(',')[1]
# 	image_bytes = base64.b64decode(face_data)
# 	np_arr = np.frombuffer(image_bytes, np.uint8)
# 	frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
# 	rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# 	# Detect faces
# 	face_locations = face_recognition.face_locations(rgb_frame)
# 	if not face_locations:
# 		messages.error(request,'No face detected')
# 		return render(request, 'registration.html')

# 	# Get face encoding
# 	face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
# 	if not face_encodings:
# 		messages.error(request,'Could not encode face')
# 		return render(request, 'registration.html')

# 	# Create user and save face encoding
# 	user = User.objects.create_user(username=username, password=password)
# 	user.role = role  # Assign role to user profile (or directly on user)
# 	user.is_face_registered = True
# 	user.save()

# 	FaceEncoding.objects.create(
# 		user=user,
# 		encoding=pickle.dumps(face_encodings[0])
# 	)
# 	user = CustomUser()
# 	user.username = username
# 	user.email = email_id
# 	user.set_password(password)
# 	user.user_type = user_type
# 	user.save()
	
# 	if user_type == CustomUser.STAFF:
# 		Staffs.objects.create(admin=user)
# 	elif user_type == CustomUser.STUDENT:
# 		Students.objects.create(admin=user)
# 	elif user_type == CustomUser.HOD:
# 		AdminHOD.objects.create(admin=user)
# 	return render(request, 'login_page.html')

	
def logout_user(request):
	logout(request)
	return HttpResponseRedirect('/')


def get_user_type_from_email(email_id):
	"""
	Returns CustomUser.user_type corresponding to the given email address
	email_id should be in following format:
	'<username>.<staff|student|hod>@<college_domain>'
	eg.: 'abhishek.staff@jecrc.com'
	"""

	try:
		email_id = email_id.split('@')[0]
		email_user_type = email_id.split('.')[1]
		return CustomUser.EMAIL_TO_USER_TYPE_MAP[email_user_type]
	except:
		return None



from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import FileSystemStorage
@csrf_exempt
def detect_bunk(request):
    if request.method == "POST":
        try:
            print("Bunk detection request received")

            # Ensure staff is authenticated
            staff = Staffs.objects.get(admin=request.user.id)

            # Ensure an image is received
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image received'}, status=400)

            print(f"Image received: {image_file.name}, Content-Type: {image_file.content_type}")

            # Read Image
            if isinstance(image_file, InMemoryUploadedFile):
                image_bytes = image_file.read()
            else:
                return JsonResponse({'error': 'Unsupported file type'}, status=400)

            # Convert Image to NumPy Array
            try:
                np_arr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    return JsonResponse({'error': 'Image decoding failed'}, status=400)

                print(f"Frame Shape: {frame.shape}, Data Type: {frame.dtype}")

                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                    print("Frame converted to uint8")

            except cv2.error as e:
                print(f"OpenCV Error: {e}")
                return JsonResponse({'error': f'Image decoding error: {e}'}, status=400)

            # Convert Image to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            print(f"RGB Frame Shape: {rgb_frame.shape}, Data Type: {rgb_frame.dtype}")

            # Detect Faces
            try:
                face_locations = face_recognition.face_locations(rgb_frame)
                if not face_locations:
                    return JsonResponse({'error': 'No face detected'}, status=400)

                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if not face_encodings:
                    return JsonResponse({'error': 'Face encoding failed'}, status=400)

                face_encoding = face_encodings[0]
            except Exception as e:
                print(f"Face Recognition Error: {e}")
                return JsonResponse({'error': f'Face recognition error: {e}'}, status=400)

            # Match Face with Database
            recognized_student = None
            for stored_face in FaceEncoding.objects.all():
                stored_encoding = pickle.loads(stored_face.encoding)
                
                # Compare captured face with stored face
                results = face_recognition.compare_faces([stored_encoding], face_encoding, tolerance=0.5)
                distance = face_recognition.face_distance([stored_encoding], face_encoding)

                print(f"Comparing with {stored_face.user.username}: Match={results}, Distance={distance}")

                if True in results:
                    recognized_student = Students.objects.get(admin=stored_face.user)
                    print(f"Student matched: {recognized_student.admin.username}")
                    break  # Stop once a match is found

            if not recognized_student:
                print("No matching student found!")

            # Save Image
            fs = FileSystemStorage(location="media/bunk_images/")
            filename = fs.save(f"bunk_{request.user.id}_{staff.id}.jpg", image_file)
            image_path = f"bunk_images/{filename}"

            # Save the bunk detection record
            bunk_record = BunkDetection.objects.create(
                staff=staff,
                student=recognized_student,
                image=image_path
            )

            print(f"Bunk detected: {recognized_student.admin.username if recognized_student else 'Unknown'}")

            return JsonResponse({
                "message": "Bunk detected successfully!",
                "student": recognized_student.admin.username if recognized_student else "Unknown",
                "image_url": bunk_record.image.url
            }, status=200)

        except Exception as e:
            print(f"Error in detect_bunk: {e}")
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def detect_bunk_page(request):
    bunks = BunkDetection.objects.all()
    context = {
        'bunks': bunks
    }
    return render(request, "staff_template/detect_bunk.html", context)


def remove_bunk(request, bunk_id):
    bunk = BunkDetection.objects.get(id=bunk_id)
    bunk.delete()
    return redirect('bunk_detection')


def get_bunk_students(request):
    students = BunkDetection.objects.all()
    return render(request, 'hod_template/detect_bunk.html', {'students': students})


