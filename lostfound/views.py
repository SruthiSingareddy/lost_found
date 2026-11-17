import os
from django.shortcuts import render,redirect
from django.http import JsonResponse
from .models import Student,Item,Claim
from .similarity import calculate_image_similarity
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.shortcuts import get_object_or_404
# Create your views here.

def home(request):

    return render(request, 'lostfound/home.html')


def register(request):

    if request.method == 'POST':

        student_name = request.POST.get('student_name')

        email = request.POST.get('email')

        mobile_number = request.POST.get('mobile_number')

        department = request.POST.get('department')

        roll_number = request.POST.get('roll_number')

        password = request.POST.get('password')

        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:

            messages.error(request, "Passwords do not match!")

            return redirect('register')

        Student.objects.create(

            student_name=student_name,

            email=email,

            mobile_number=mobile_number,

            department=department,

            roll_number=roll_number,

            password=make_password(password)

        )

        messages.success(request, "Student registered successfully!")

        return redirect('register')

    return render(request, 'lostfound/register.html')
def report_item(request):

    students = Student.objects.all()

    if request.method == 'POST':

        item_name = request.POST.get('item_name')
        category = request.POST.get('category')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        image = request.FILES.get('image')
        location = request.POST.get('location')
        date = request.POST.get('date')
        item_type = request.POST.get('item_type')
        student_id = request.POST.get('student')

        student = Student.objects.get(id=student_id)

        Item.objects.create(
            item_name=item_name,
            category=category,
            description=description,
            location=location,
            date=date,
            item_type=item_type,
            student=student,
            image=image
        )
        messages.success(request, "Item reported successfully!")

        return redirect('report_item')
    

    return render(request, 'lostfound/report.html', {'students': students})
def items(request):

    # Get all items
    item_list = Item.objects.all().order_by('-date')


    # Search
    search_query = request.GET.get('q', '').strip()


    if search_query:

        item_list = item_list.filter(

            Q(item_name__icontains=search_query) |

            Q(category__icontains=search_query) |

            Q(location__icontains=search_query) |

            Q(description__icontains=search_query)

        )


    # Lost / Found filter
    filter_type = request.GET.get('type', 'all')


    if filter_type in ['Lost', 'Found']:

        item_list = item_list.filter(
            item_type=filter_type
        )


    # Send data to template
    context = {

        'items': item_list,

        'search_query': search_query,

        'filter_type': filter_type,

    }


    return render(
        request,
        'lostfound/items.html',
        context
    )


def search_items(request):

    items = Item.objects.all()

    # Search text
    query = request.GET.get('q', '').strip()

    if query:
        items = items.filter(
            Q(item_name__icontains=query) |
            Q(category__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )

    # Category filter
    category = request.GET.get('category', '')

    if category:
        items = items.filter(category=category)

    # Lost / Found filter
    item_type = request.GET.get('item_type', '')

    if item_type in ['Lost', 'Found']:
        items = items.filter(item_type=item_type)

    # Status filter
    status = request.GET.get('status', '')

    if status:
        items = items.filter(status=status)

    # Date filters
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    parsed_from_date = parse_date(from_date) if from_date else None
    parsed_to_date = parse_date(to_date) if to_date else None

    if parsed_from_date:
        items = items.filter(date__date__gte=parsed_from_date)

    if parsed_to_date:
        items = items.filter(date__date__lte=parsed_to_date)

    # Dropdown values
    categories = (
        Item.objects
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    statuses = (
        Item.objects
        .values_list('status', flat=True)
        .distinct()
        .order_by('status')
    )

    items = items.order_by('-date')

    context = {
        'items': items,
        'categories': categories,
        'statuses': statuses,
        'query': query,
        'selected_category': category,
        'selected_type': item_type,
        'selected_status': status,
        'from_date': from_date,
        'to_date': to_date,
    }

    return render(request, 'lostfound/search_item.html', context)


def submit_claim(request):
    student_session_id = request.session.get('student_id')
    logged_in_student = None
    if student_session_id:
        logged_in_student = Student.objects.filter(id=student_session_id).first()

    students = Student.objects.all().order_by('student_name')
    items = Item.objects.filter(
        item_type='Found',
        status='Active'
    ).order_by('-date')

    # Optional item preselection (e.g. ?item_id=4)
    selected_item_id = request.GET.get('item_id', '')

    if request.method == 'POST':
        # Identify student
        if logged_in_student:
            student = logged_in_student
        else:
            student_id = request.POST.get('student')
            if not student_id:
                messages.error(request, "Please select or verify your student profile.")
                return redirect('submit_claim')
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                messages.error(request, "Selected student profile does not exist.")
                return redirect('submit_claim')

        item_id = request.POST.get('item')
        if not item_id:
            messages.error(request, "Please select the found item you wish to claim.")
            return redirect('submit_claim')

        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            messages.error(request, "Selected found item not found in database.")
            return redirect('submit_claim')

        existing_claim = Claim.objects.filter(
            student=student,
            item=item,
            claim_status__in=['Pending', 'Approved']
        ).exists()

        if existing_claim:
            messages.error(
                request,
                "You have already submitted an active claim for this item."
            )
            return redirect('submit_claim')

        claim_description = request.POST.get('claim_description', '').strip()
        contact_number = request.POST.get('contact_number', '').strip() or student.mobile_number
        lost_date = request.POST.get('lost_date') or None
        lost_location = request.POST.get('lost_location', '').strip()
        additional_details = request.POST.get('additional_details', '').strip()
        lost_item_image = request.FILES.get('lost_item_image')

        similarity_score = None
        similarity_result = None

        if lost_item_image:
            # File validation
            max_size = 5 * 1024 * 1024  # 5MB
            if lost_item_image.size > max_size:
                messages.error(request, "Uploaded lost item image exceeds the 5MB size limit.")
                return redirect('submit_claim')

            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            ext = os.path.splitext(lost_item_image.name)[1].lower()
            if ext not in allowed_extensions:
                messages.error(request, "Invalid image format. Supported formats are JPG, JPEG, PNG, and WEBP.")
                return redirect('submit_claim')

            # Real Computer Vision comparison with selected found item
            found_img_path = item.image.path if item.image and os.path.exists(item.image.path) else None
            sim_res = calculate_image_similarity(lost_item_image, found_img_path)
            similarity_score = sim_res['score']
            similarity_result = sim_res['result_label']

        claim = Claim.objects.create(
            student=student,
            item=item,
            claim_description=claim_description,
            contact_number=contact_number,
            claim_status='Pending',
            lost_item_image=lost_item_image,
            lost_date=lost_date,
            lost_location=lost_location,
            additional_details=additional_details,
            similarity_score=similarity_score,
            similarity_result=similarity_result
        )

        messages.success(
            request,
            f"Claim submitted successfully for '{item.item_name}'! Initial status is Pending verification."
        )

        if logged_in_student:
            return redirect('student_dashboard')
        return redirect('submit_claim')

    return render(
        request,
        'lostfound/claim.html',
        {
            'students': students,
            'items': items,
            'logged_in_student': logged_in_student,
            'selected_item_id': selected_item_id,
        }
    )


def compare_claim_images(request):
    """
    AJAX endpoint for real-time computer vision matching between
    uploaded lost-item photo and the selected found-item photo.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST request required.'}, status=405)

    item_id = request.POST.get('item_id')
    lost_image = request.FILES.get('lost_image')

    if not item_id:
        return JsonResponse({'success': False, 'error': 'No found item selected.'}, status=400)

    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Found item does not exist.'}, status=404)

    if not lost_image:
        return JsonResponse({'success': False, 'error': 'No photograph uploaded.'}, status=400)

    # Validate file extension
    allowed = ('.jpg', '.jpeg', '.png', '.webp')
    ext = os.path.splitext(lost_image.name)[1].lower()
    if ext not in allowed:
        return JsonResponse({'success': False, 'error': 'Format not supported. Please upload JPG, JPEG, PNG, or WEBP.'}, status=400)

    # Validate file size (max 5MB)
    if lost_image.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'Image exceeds the maximum allowed size of 5MB.'}, status=400)

    found_img_path = item.image.path if item.image and os.path.exists(item.image.path) else None
    result = calculate_image_similarity(lost_image, found_img_path)

    return JsonResponse({
        'success': True,
        'score': result['score'],
        'result_label': result['result_label'],
        'result_badge': result['result_badge'],
        'explanation': result['explanation'],
        'breakdown': result['breakdown'],
        'has_reference': result['has_reference'],
        'found_image_url': item.image.url if item.image else None,
        'item_name': item.item_name,
        'category': item.category,
        'location': item.location,
        'date': item.date.strftime('%Y-%m-%d') if item.date else '',
    })


@login_required
def manage_claims(request):
    claims = Claim.objects.all().select_related('student', 'item').order_by('-created_at')

    status_filter = request.GET.get('status', 'all')
    if status_filter in ['Pending', 'Approved', 'Rejected']:
        claims = claims.filter(claim_status=status_filter)

    total_count = Claim.objects.count()
    pending_count = Claim.objects.filter(claim_status='Pending').count()
    approved_count = Claim.objects.filter(claim_status='Approved').count()
    rejected_count = Claim.objects.filter(claim_status='Rejected').count()

    return render(
        request,
        'lostfound/manage_claims.html',
        {
            'claims': claims,
            'status_filter': status_filter,
            'total_count': total_count,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
        }
    )


@login_required
def approve_claim(request, claim_id):
    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()
        with transaction.atomic():
            claim = Claim.objects.select_for_update().get(id=claim_id)
            item = Item.objects.select_for_update().get(id=claim.item_id)

            if claim.claim_status != 'Approved':
                claim.claim_status = 'Approved'
                if admin_note:
                    claim.admin_note = admin_note
                claim.save()

                item.status = 'Returned'
                item.save()

                messages.success(
                    request,
                    f"Claim #{claim.id} for '{item.item_name}' by {claim.student.student_name} was Approved. Item status set to Returned."
                )

    return redirect('manage_claims')


@login_required
def reject_claim(request, claim_id):
    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()
        claim = Claim.objects.get(id=claim_id)
        claim.claim_status = 'Rejected'
        if admin_note:
            claim.admin_note = admin_note
        claim.save()

        messages.info(
            request,
            f"Claim #{claim.id} for '{claim.item.item_name}' was Rejected."
        )

    return redirect('manage_claims')



@login_required
def dashboard(request):

    total_students = Student.objects.count()

    total_lost_items = Item.objects.filter(
        item_type='Lost'
    ).count()

    total_found_items = Item.objects.filter(
        item_type='Found'
    ).count()

    pending_claims = Claim.objects.filter(
        claim_status='Pending'
    ).count()

    approved_claims = Claim.objects.filter(
        claim_status='Approved'
    ).count()

    rejected_claims = Claim.objects.filter(
        claim_status='Rejected'
    ).count()

    context = {
        'total_students': total_students,
        'total_lost_items': total_lost_items,
        'total_found_items': total_found_items,
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
    }

    return render(
        request,
        'lostfound/dashboard.html',
        context
    )
def admin_logout(request):

    logout(request)

    return redirect('home')

# Student Login

def student_login(request):

    if request.method == 'POST':

        email = request.POST.get('email')

        password = request.POST.get('password')

        try:

            student = Student.objects.get(email=email)

            if check_password(password, student.password):

                request.session['student_id'] = student.id

                messages.success(request, "Login successful!")

                return redirect('student_dashboard')

            else:

                messages.error(request, "Invalid password!")

        except Student.DoesNotExist:

            messages.error(request, "Email not registered!")

    return render(request, 'lostfound/student_login.html')
# Student Dashboard


# Student Dashboard

def student_dashboard(request):

    student_id = request.session.get('student_id')

    if not student_id:

        messages.error(request, "Please login first!")

        return redirect('student_login')

    student = Student.objects.get(id=student_id)

    # Get student's reported items
    student_items = Item.objects.filter(
        student=student
    )
    my_lost_items = student_items.filter(
    item_type='Lost'
    )
    my_found_items = student_items.filter(
    item_type='Found'
    )

    # Get student's submitted claims
    student_claims = Claim.objects.filter(
        student=student
    )
    my_claims = student_claims

    # Count lost items
    total_lost_items = student_items.filter(
        item_type='Lost'
    ).count()

    # Count found items
    total_found_items = student_items.filter(
        item_type='Found'
    ).count()

    # Count submitted claims
    total_claims = student_claims.count()

    # Count pending claims
    pending_claims = student_claims.filter(
        claim_status='Pending'
    ).count()

    # Send data to HTML
    context = {

        'student': student,

        'total_lost_items': total_lost_items,

        'total_found_items': total_found_items,

        'total_claims': total_claims,

        'pending_claims': pending_claims,

        'my_claims': my_claims,

        'my_lost_items': my_lost_items,
        
        'my_found_items': my_found_items,

    }

    return render(request,'lostfound/student_dashboard.html',context)

# Admin Dashboard

@login_required
def admin_dashboard(request):

    total_students = Student.objects.count()

    total_lost_items = Item.objects.filter(
        item_type='Lost'
    ).count()

    total_found_items = Item.objects.filter(
        item_type='Found'
    ).count()

    total_claims = Claim.objects.count()

    pending_claims = Claim.objects.filter(
        claim_status='Pending'
    ).count()

    approved_claims = Claim.objects.filter(
        claim_status='Approved'
    ).count()

    rejected_claims = Claim.objects.filter(
        claim_status='Rejected'
    ).count()

    context = {
        'total_students': total_students,
        'total_lost_items': total_lost_items,
        'total_found_items': total_found_items,
        'total_claims': total_claims,
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
    }

    return render(
        request,
        'lostfound/admin_dashboard.html',
        context
    )
# View All Students
@login_required
def view_students(request):

    students = Student.objects.all()

    context = {
        'students': students
    }

    return render(
        request,
        'lostfound/view_students.html',
        context
    )
# Admin View All Items
@login_required
def view_all_items(request):

    items = Item.objects.all()

    context = {
        'items': items
    }

    return render(
        request,
        'lostfound/view_all_items.html',
        context
    )
# Admin Update Item Status
@login_required
def update_item_status(request, pk):

    item = Item.objects.get(id=pk)

    if request.method == 'POST':

        status = request.POST.get('status')

        item.status = status

        item.save()

        messages.success(
            request,
            "Item status updated successfully!"
        )

        return redirect('view_all_items')

    return render(
        request,
        'lostfound/update_item_status.html',
        {'item': item}
    )

# Edit Photo of Previously Reported Item
def edit_item_image(request, item_id):

    student_id = request.session.get('student_id')

    if not student_id:
        messages.error(request, "Please login first!")
        return redirect('student_login')

    item = get_object_or_404(
        Item,
        id=item_id,
        student_id=student_id
    )

    if request.method == 'POST':

        uploaded_image = request.FILES.get('image')

        if uploaded_image:
            item.image = uploaded_image
            item.save()

            messages.success(
                request,
                "Photo updated successfully!"
            )

            return redirect('student_dashboard')

        messages.error(request, "Please select an image.")

    return render(
        request,
        'lostfound/edit_item_image.html',
        {'item': item}
    )
def student_logout(request):
    request.session.pop('student_id', None)

    messages.success(request, "You have logged out successfully!")

    return redirect('/product/products/')