from django.shortcuts import render,HttpResponse, redirect,HttpResponseRedirect
from django.contrib.auth import logout, authenticate, login
from .models import CustomUser, FaceEncoding, Staffs, Students, AdminHOD
from django.contrib import messages
import cv2
import face_recognition
import numpy as np
import pickle
import base64
def home(request):
	return render(request, 'home.html')


def contact(request):
	return render(request, 'contact.html')


def loginUser(request):
	return render(request, 'login_page.html')

def doLogin(request):
    if request.method == 'POST':
        try:
            print("Login request received")
            from django.http import JsonResponse
            # Ensure an image file is received
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image received'}, status=400)
			
			
			#print("Image received")
            image_bytes = image_file.read()
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({'error': 'No face detected'}, status=400)

            # Get face encoding
            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)
            if not face_encoding:
                return JsonResponse({'error': 'Face encoding failed'}, status=400)

            face_encoding = face_encoding[0]  # Extract first encoding
            
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
                matches = face_recognition.compare_faces([existing_encoding], face_encodings[0])
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

            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')

        except Exception as e:
            print("Error:", e)
            messages.error(request, f"An error occurred: {str(e)}")
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
