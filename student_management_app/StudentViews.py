from django.shortcuts import render, redirect
from django.contrib import messages

import datetime 
from .models import BunkDetection, CustomUser,  Courses, Subjects, Students, Attendance, AttendanceReport, LeaveReportStudent, FeedBackStudent, StudentResult


def student_home(request):
    print(request.user.id)
    print(request.user.id)
    student_obj = Students.objects.get(admin=request.user.id)
    student = get_object_or_404(Students, admin=request.user)
    total_attendance =   AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present = AttendanceReport.objects.filter(student_id=student_obj, status=True).count()
    attendance_absent =  AttendanceReport.objects.filter(student_id=student_obj, status=False).count()
    bunk_records = BunkDetection.objects.filter(student=student).order_by("-detected_at")
    course_obj = Courses.objects.get(id=student_obj.course_id.id)
    total_subjects = Subjects.objects.filter(course_id=course_obj).count()

    subject_name = []
    data_present = []
    data_absent = []
    subject_data = Subjects.objects.filter(course_id=student_obj.course_id)
    for subject in subject_data:
        attendance = Attendance.objects.filter(subject_id=subject.id)
        attendance_present_count = AttendanceReport.objects.filter(attendance_id__in=attendance, status=True, student_id=student_obj.id).count()
        attendance_absent_count = AttendanceReport.objects.filter(attendance_id__in=attendance, status=False, student_id=student_obj.id).count()
        subject_name.append(subject.subject_name)
        data_present.append(attendance_present_count)
        data_absent.append(attendance_absent_count)
    attendance_percentage = 0
    if total_attendance > 0:  # Avoid division by zero
        attendance_percentage = round((attendance_present / total_attendance) * 100, 2)
    context={
         'student_id': student,
        "total_attendance": total_attendance,
        "attendance_present": attendance_present,
        "attendance_absent": attendance_absent,
        "total_subjects": total_subjects,
        "subject_name": subject_name,
        "data_present": data_present,
        "data_absent": data_absent,
        "bunk_records": bunk_records,
        'attendance_percentage': attendance_percentage,
    }
    return render(request, "student_template/student_home_template.html",context)


def student_view_attendance(request):
    student = Students.objects.get(admin=request.user.id) # Getting Logged in Student Data
    course = student.course_id # Getting Course Enrolled of LoggedIn Student
    # course = Courses.objects.get(id=student.course_id.id) # Getting Course Enrolled of LoggedIn Student
    subjects = Subjects.objects.filter(course_id=course) # Getting the Subjects of Course Enrolled
    context = {
        "subjects": subjects
    }
    return render(request, "student_template/student_view_attendance.html", context)


def student_view_attendance_post(request):


    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect('student_view_attendance')
    else:
        # Getting all the Input Data
        subject_id = request.POST.get('subject')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        start_date_parse = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_parse = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()


        subject_obj = Subjects.objects.get(id=subject_id)
        
        user_obj = CustomUser.objects.get(id=request.user.id)
        
        stud_obj = Students.objects.get(admin=user_obj)
        attendance = Attendance.objects.filter(attendance_date__range=(start_date_parse, end_date_parse), subject_id=subject_obj)


        attendance_reports = AttendanceReport.objects.filter(attendance_id__in=attendance, student_id=stud_obj)

        context = {
            "subject_obj": subject_obj,
            "attendance_reports": attendance_reports
        }

        return render(request, 'student_template/student_attendance_data.html', context)
       

def student_apply_leave(request):
    student_obj = Students.objects.get(admin=request.user.id)
    leave_data = LeaveReportStudent.objects.filter(student_id=student_obj)
    context = {
        "leave_data": leave_data
    }
    return render(request, 'student_template/student_apply_leave.html', context)


def student_apply_leave_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect('student_apply_leave')
    else:
        leave_date = request.POST.get('leave_date')
        leave_message = request.POST.get('leave_message')

        student_obj = Students.objects.get(admin=request.user.id)
        try:
            leave_report = LeaveReportStudent(student_id=student_obj, leave_date=leave_date, leave_message=leave_message, leave_status=0)
            leave_report.save()
            messages.success(request, "Applied for Leave.")
            return redirect('student_apply_leave')
        except:
            messages.error(request, "Failed to Apply Leave")
            return redirect('student_apply_leave')


def student_feedback(request):
    student_obj = Students.objects.get(admin=request.user.id)
    feedback_data = FeedBackStudent.objects.filter(student_id=student_obj)
    context = {
        "feedback_data": feedback_data
    }
    return render(request, 'student_template/student_feedback.html', context)


def student_feedback_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method.")
        return redirect('student_feedback')
    else:
        feedback = request.POST.get('feedback_message')
        student_obj = Students.objects.get(admin=request.user.id)

        try:
            add_feedback = FeedBackStudent(student_id=student_obj, feedback=feedback, feedback_reply="")
            add_feedback.save()
            messages.success(request, "Feedback Sent.")
            return redirect('student_feedback')
        except:
            messages.error(request, "Failed to Send Feedback.")
            return redirect('student_feedback')


def student_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    student = Students.objects.get(admin=user)

    context={
        "user": user,
        "student": student
    }
    return render(request, 'student_template/student_profile.html', context)


def student_profile_update(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method!")
        return redirect('student_profile')
    else:
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        address = request.POST.get('address')

        try:
            customuser = CustomUser.objects.get(id=request.user.id)
            customuser.first_name = first_name
            customuser.last_name = last_name
            if password != None and password != "":
                customuser.set_password(password)
            customuser.save()

            student = Students.objects.get(admin=customuser.id)
            student.address = address
            student.save()
            
            messages.success(request, "Profile Updated Successfully")
            return redirect('student_profile')
        except:
            messages.error(request, "Failed to Update Profile")
            return redirect('student_profile')


def student_view_result(request):
    student = Students.objects.get(admin=request.user.id)
    student_result = StudentResult.objects.filter(student_id=student.id)
    context = {
        "student_result": student_result,
    }
    return render(request, "student_template/student_view_result.html", context)





from django.shortcuts import render,get_object_or_404
from .models import TimeTable,Students, StudentFees,FeesStructure

def student_view_timetable(request):
    student = Students.objects.get(admin=request.user.id)
    timetables = TimeTable.objects.filter(course_id=student.course_id)
    context = {
        'timetables': timetables,
    }
    return render(request, 'student_template/student_view_timetable.html', context)

# def view_fee_details(request, student_id):
#     student = get_object_or_404(Students, id=student_id)
#     try:
#         # Get the student's fee details
#         student_fees = StudentFees.objects.get(student=student)
#     except StudentFees.DoesNotExist:
#         student_fees = None

#     context = {
#         'student': student,
#         'student_fees': student_fees,
#         'totalfees': student_fees.total_fees,
#         'paidfees' : student_fees.paid_fees,
#         'balance': student_fees.total_fees - student_fees.paid_fees if student_fees else 0,
#     }
#     print(student_fees)
#     return render(request, 'student_template/fee_details.html',context)


def view_fee_details(request, student_id):
    student = get_object_or_404(Students, id=student_id)
    try:
        student_fees = StudentFees.objects.get(student=student)
        paid_fees = student_fees.paid_fees
        total_fees = student.default_fees  # Access the total_fee from FeesStructure
    except StudentFees.DoesNotExist:
        student_fees = None
        paid_fees = 0
        total_fees = student.total_fees

    balance = total_fees - paid_fees

    context = {
        'student': student,
        'student_fees': student_fees,
        'total_fees': total_fees,
        'paid_fees': paid_fees,
        'balance': balance,
    }

    return render(request, 'student_template/fee_details.html', context)


def bunked_classes(request):
    student = Students.objects.get(admin=request.user)  # Get the logged-in student
    bunk_records = BunkDetection.objects.filter(student=student).order_by("-detected_at")  # Fetch bunk records

    context = {
        "bunk_records": bunk_records,
    }
    return render(request, "student_template/bunked_classes.html", context)