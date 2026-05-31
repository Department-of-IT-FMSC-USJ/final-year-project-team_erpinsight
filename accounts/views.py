from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, AdminSignupForm, EmployeeSignupForm, ChangePasswordForm
from .models import CustomUser, Company, BusinessProcess, RegisteredEmployee, EmployeeInvitation, EvaluationQuestion, EvaluationResponse, CategoryFeedback
from django.db.models import Avg, Count
import json
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch


def login_view(request):
    """Unified login for all roles."""
    if request.user.is_authenticated:
        return redirect('accounts:redirect')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('accounts:redirect')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def redirect_after_login(request):
    """Redirect to the correct dashboard based on role."""
    role = request.user.role
    if role == CustomUser.SUPER_ADMIN:
        return redirect('accounts:super_admin_dashboard')
    elif role == CustomUser.ADMIN:
        return redirect('accounts:admin_dashboard')
    elif role == CustomUser.EMPLOYEE:
        return redirect('accounts:employee_dashboard')
    return redirect('accounts:login')


def admin_signup_view(request):
    """Admin registration using company code."""
    if request.user.is_authenticated:
        return redirect('accounts:redirect')

    form = AdminSignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created! Welcome, {user.username}.')
            return redirect('accounts:admin_dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'accounts/admin_signup.html', {'form': form})


def employee_signup_view(request):
    """Employee registration — email must be pre-registered by Admin."""
    if request.user.is_authenticated:
        return redirect('accounts:redirect')

    form = EmployeeSignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created! Welcome, {user.username}.')
            return redirect('accounts:employee_dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'accounts/employee_signup.html', {'form': form})


# ─── Dashboards (placeholders until fully built) ──────────────────────────────

@login_required
def super_admin_dashboard(request):
    if not request.user.is_super_admin():
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')
    company = request.user.company
    return render(request, 'accounts/super_admin_dashboard.html', {'company': company})



@login_required
def admin_dashboard(request):
    if not request.user.is_admin() and not request.user.is_super_admin():
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')
    
    company = request.user.company

    # Setup checklist checks
    has_processes   = BusinessProcess.objects.filter(company=company).exists()
    has_employees   = RegisteredEmployee.objects.filter(company=company).exists()
    has_questions   = EvaluationQuestion.objects.filter(company=company).exists()
    has_evaluations = EvaluationResponse.objects.filter(
        business_process__company=company
    ).exists()

    checklist = {
        'processes':   has_processes,
        'employees':   has_employees,
        'questions':   has_questions,
        'evaluations': has_evaluations,
        'analytics':   has_evaluations,  # analytics available once evaluations exist
    }

    # Count stats
    process_count  = BusinessProcess.objects.filter(company=company).count()
    employee_count = RegisteredEmployee.objects.filter(company=company).count()
    eval_count     = EvaluationResponse.objects.filter(
        business_process__company=company
    ).values('employee').distinct().count()

    return render(request, 'accounts/admin_dashboard.html', {
        'checklist':      checklist,
        'process_count':  process_count,
        'employee_count': employee_count,
        'eval_count':     eval_count,
    })


@login_required
def employee_dashboard(request):
    if not request.user.is_employee():
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')
    
    employee = request.user
    company = employee.company

    # Get assigned process
    registered = RegisteredEmployee.objects.filter(
        email=employee.email,
        company=company
    ).first()

    assigned_process = None
    has_submitted = False

    if registered:
        try:
            assigned_process = BusinessProcess.objects.get(
                name=registered.business_process,
                company=company
            )
            # Check if already submitted
            has_submitted = EvaluationResponse.objects.filter(
                employee=employee,
                business_process=assigned_process
            ).exists()
        except BusinessProcess.DoesNotExist:
            pass

    return render(request, 'accounts/employee_dashboard.html', {
        'assigned_process': assigned_process,
        'has_submitted': has_submitted,
    })


@login_required
def change_password_view(request):
    form = ChangePasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = request.user
            if not user.check_password(form.cleaned_data['old_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
                return redirect('accounts:redirect')

    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def register_company(request):
    if not request.user.is_super_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        name = request.POST.get('name')
        erp_type = request.POST.get('erp_type')
        industry = request.POST.get('industry')
        company = Company.objects.create(name=name, erp_type=erp_type, industry=industry)
        request.user.company = company
        request.user.save()
        messages.success(request, f'Company registered! Code: {company.company_code}')
        return redirect('accounts:super_admin_dashboard')
    return redirect('accounts:super_admin_dashboard')


@login_required
def business_processes(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    company = request.user.company
    processes = BusinessProcess.objects.filter(company=company)
    return render(request, 'accounts/business_processes.html', {
        'processes': processes,
    })


@login_required
def add_business_process(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        name = request.POST.get('name')
        process_type = request.POST.get('process_type')
        description = request.POST.get('description')
        company = request.user.company

        # If predefined selected, use its label as name
        if process_type != 'custom':
            predefined_names = dict(BusinessProcess.PREDEFINED_PROCESSES)
            name = predefined_names.get(process_type, name)

        if BusinessProcess.objects.filter(company=company, name=name).exists():
            messages.error(request, f'Process "{name}" already exists.')
        else:
            BusinessProcess.objects.create(
                company=company,
                name=name,
                process_type=process_type,
                description=description
            )
            messages.success(request, f'Business process "{name}" added successfully!')
        return redirect('accounts:business_processes')
    return redirect('accounts:business_processes')


@login_required
def edit_business_process(request, pk):
    if not request.user.is_admin():
        return redirect('accounts:login')
    process = BusinessProcess.objects.get(pk=pk, company=request.user.company)
    if request.method == 'POST':
        process.name = request.POST.get('name')
        process.description = request.POST.get('description')
        process.is_active = request.POST.get('is_active') == 'on'
        process.save()
        messages.success(request, 'Process updated successfully!')
        return redirect('accounts:business_processes')
    return render(request, 'accounts/edit_business_process.html', {'process': process})


@login_required
def delete_business_process(request, pk):
    if not request.user.is_admin():
        return redirect('accounts:login')
    process = BusinessProcess.objects.get(pk=pk, company=request.user.company)
    process.delete()
    messages.success(request, 'Process deleted successfully!')
    return redirect('accounts:business_processes')


#employee creation by manager

@login_required
def employees(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    company = request.user.company
    registered_employees = RegisteredEmployee.objects.filter(company=company)
    processes = BusinessProcess.objects.filter(company=company, is_active=True)
    return render(request, 'accounts/employees.html', {
        'registered_employees': registered_employees,
        'processes': processes,
    })


@login_required
def add_employee(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        email = request.POST.get('email')
        process_id = request.POST.get('process')
        company = request.user.company
        process = BusinessProcess.objects.get(pk=process_id, company=company)

        if RegisteredEmployee.objects.filter(company=company, email=email).exists():
            messages.error(request, f'Email "{email}" is already registered.')
            return redirect('accounts:employees')

        # Create registered employee
        RegisteredEmployee.objects.create(
            company=company,
            email=email,
            business_process=process.name
        )

        # Create invitation token
        invitation = EmployeeInvitation.objects.create(
            company=company,
            email=email,
            business_process=process.name,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Build invite link
        invite_link = request.build_absolute_uri(
            f'/accounts/invite/{invitation.token}/'
        )

        messages.success(request, f'Employee registered! Invite link generated.')
        return render(request, 'accounts/invite_link.html', {
            'invite_link': invite_link,
            'email': email,
            'process': process.name,
            'expires_at': invitation.expires_at,
        })

    return redirect('accounts:employees')


@login_required
def delete_employee(request, pk):
    if not request.user.is_admin():
        return redirect('accounts:login')
    employee = RegisteredEmployee.objects.get(pk=pk, company=request.user.company)
    employee.delete()
    messages.success(request, 'Employee removed successfully!')
    return redirect('accounts:employees')


def employee_invite_signup(request, token):
    try:
        invitation = EmployeeInvitation.objects.get(token=token, is_used=False)
    except EmployeeInvitation.DoesNotExist:
        messages.error(request, 'This invitation link is invalid or already used.')
        return redirect('accounts:login')

    if invitation.is_expired():
        messages.error(request, 'This invitation link has expired. Please ask your Manager for a new one.')
        return redirect('accounts:login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/invite_signup.html', {
                'invitation': invitation,
            })

        if CustomUser.objects.filter(email=invitation.email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'accounts/invite_signup.html', {
                'invitation': invitation,
            })

        # Create employee account
        user = CustomUser.objects.create_user(
            email=invitation.email,
            username=username,
            password=password1,
            role=CustomUser.EMPLOYEE,
            company=invitation.company,
        )

        # Mark invitation as used
        invitation.is_used = True
        invitation.save()

        # Mark registered employee as signed up
        RegisteredEmployee.objects.filter(
            email=invitation.email,
            company=invitation.company
        ).update(is_registered=True)

        login(request, user)
        messages.success(request, f'Welcome, {username}! Your account has been created.')
        return redirect('accounts:employee_dashboard')

    return render(request, 'accounts/invite_signup.html', {
        'invitation': invitation,
    })

#questions creation

@login_required
def evaluation_questions(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    company = request.user.company
    processes = BusinessProcess.objects.filter(company=company, is_active=True)
    selected_process = None
    questions_by_category = {}

    process_id = request.GET.get('process')
    if process_id:
        try:
            selected_process = BusinessProcess.objects.get(pk=process_id, company=company)

            # Load predefined template questions for this process type
            predefined = EvaluationQuestion.objects.filter(
                process_type=selected_process.process_type,
                company=None,
                business_process=None,
            )

            # Load company custom questions for this process
            custom = EvaluationQuestion.objects.filter(
                company=company,
                business_process=selected_process,
                question_type='custom',
            )

            all_questions = list(predefined) + list(custom)

            # Group by category
            for q in all_questions:
                cat = q.get_category_display()
                if cat not in questions_by_category:
                    questions_by_category[cat] = []
                questions_by_category[cat].append(q)

        except BusinessProcess.DoesNotExist:
            pass

    return render(request, 'accounts/evaluation_questions.html', {
        'processes': processes,
        'selected_process': selected_process,
        'questions_by_category': questions_by_category,
        'process_id': process_id,
    })


@login_required
def toggle_question(request, pk):
    if not request.user.is_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        company = request.user.company
        process_id = request.POST.get('process_id')

        try:
            # Try company-specific override first
            q = EvaluationQuestion.objects.get(pk=pk, company=company)
            q.is_active = not q.is_active
            q.save()
        except EvaluationQuestion.DoesNotExist:
            # Create company-specific override for predefined question
            original = EvaluationQuestion.objects.get(pk=pk)
            EvaluationQuestion.objects.create(
                company=company,
                business_process=BusinessProcess.objects.get(pk=process_id),
                process_type=original.process_type,
                category=original.category,
                question_text=original.question_text,
                question_type='predefined',
                diagnosis_tag=original.diagnosis_tag,
                diagnosis_message=original.diagnosis_message,
                is_active=False,
            )

    return redirect(f"/accounts/questions/?process={request.POST.get('process_id')}")


@login_required
def add_custom_question(request):
    if not request.user.is_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        company = request.user.company
        process_id = request.POST.get('process_id')
        category = request.POST.get('category')
        question_text = request.POST.get('question_text')
        diagnosis_tag = request.POST.get('diagnosis_tag')
        diagnosis_message = request.POST.get('diagnosis_message')

        process = BusinessProcess.objects.get(pk=process_id, company=company)

        EvaluationQuestion.objects.create(
            company=company,
            business_process=process,
            process_type=process.process_type,
            category=category,
            question_text=question_text,
            question_type='custom',
            diagnosis_tag=diagnosis_tag,
            diagnosis_message=diagnosis_message,
            is_active=True,
        )
        messages.success(request, 'Custom question added successfully!')
    return redirect(f"/accounts/questions/?process={process_id}")


@login_required
def delete_custom_question(request, pk):
    if not request.user.is_admin():
        return redirect('accounts:login')
    process_id = request.POST.get('process_id')
    q = EvaluationQuestion.objects.get(pk=pk, company=request.user.company, question_type='custom')
    q.delete()
    messages.success(request, 'Question deleted successfully!')
    return redirect(f"/accounts/questions/?process={process_id}")

@login_required
def employee_evaluation(request):
    if not request.user.is_employee():
        return redirect('accounts:login')

    employee = request.user
    company = employee.company

    # Get assigned process
    registered = RegisteredEmployee.objects.filter(
        email=employee.email,
        company=company
    ).first()

    if not registered:
        messages.error(request, 'You are not assigned to any business process.')
        return redirect('accounts:employee_dashboard')

    try:
        assigned_process = BusinessProcess.objects.get(
            name=registered.business_process,
            company=company
        )
    except BusinessProcess.DoesNotExist:
        messages.error(request, 'Your assigned process was not found.')
        return redirect('accounts:employee_dashboard')

    # Check if already submitted
    if EvaluationResponse.objects.filter(
        employee=employee,
        business_process=assigned_process
    ).exists():
        messages.warning(request, 'You have already submitted your evaluation.')
        return redirect('accounts:employee_dashboard')

    # Get active questions for this process
    predefined = EvaluationQuestion.objects.filter(
        process_type=assigned_process.process_type,
        company=None,
        business_process=None,
        is_active=True,
    )

    # Check for disabled overrides
    disabled_ids = EvaluationQuestion.objects.filter(
        company=company,
        business_process=assigned_process,
        is_active=False,
    ).values_list('question_text', flat=True)

    predefined = predefined.exclude(question_text__in=disabled_ids)

    custom = EvaluationQuestion.objects.filter(
        company=company,
        business_process=assigned_process,
        question_type='custom',
        is_active=True,
    )

    all_questions = list(predefined) + list(custom)

    # Group by category
    questions_by_category = {}
    category_order = [
        'System Quality',
        'Information Quality',
        'Process Efficiency',
        'User Satisfaction',
        'Perceived ROI',
    ]

    for q in all_questions:
        cat = q.get_category_display()
        if cat not in questions_by_category:
            questions_by_category[cat] = []
        questions_by_category[cat].append(q)

    # Sort by category order
    ordered = {k: questions_by_category[k] for k in category_order if k in questions_by_category}

    if request.method == 'POST':
        errors = []

        # Validate all questions answered
        for q in all_questions:
            rating = request.POST.get(f'question_{q.pk}')
            if not rating:
                errors.append(f'Please answer all questions.')
                break

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/employee_evaluation.html', {
                'assigned_process': assigned_process,
                'questions_by_category': ordered,
            })

        # Save responses
        for q in all_questions:
            rating = request.POST.get(f'question_{q.pk}')
            if rating:
                EvaluationResponse.objects.create(
                    employee=employee,
                    business_process=assigned_process,
                    question=q,
                    rating=int(rating),
                )

        # Save category feedback
        for category_name in ordered.keys():
            category_key = category_name.lower().replace(' ', '_')
            feedback_text = request.POST.get(f'feedback_{category_key}', '').strip()
            if feedback_text:
                CategoryFeedback.objects.create(
                    employee=employee,
                    business_process=assigned_process,
                    category=category_key,
                    feedback_text=feedback_text,
                )

        messages.success(request, 'Evaluation submitted successfully! Thank you.')
        return redirect('accounts:evaluation_submitted')

    return render(request, 'accounts/employee_evaluation.html', {
        'assigned_process': assigned_process,
        'questions_by_category': ordered,
    })


@login_required
def evaluation_submitted(request):
    if not request.user.is_employee():
        return redirect('accounts:login')
    return render(request, 'accounts/evaluation_submitted.html')

#scoring calculation
@login_required
def analytics_dashboard(request):
    if not request.user.is_admin():
        return redirect('accounts:login')

    company = request.user.company
    processes = BusinessProcess.objects.filter(company=company, is_active=True)

    selected_process = None
    analytics_data = None
    compare_process = None
    compare_data = None

    process_id = request.GET.get('process')
    compare_id = request.GET.get('compare')

    if process_id:
        try:
            selected_process = BusinessProcess.objects.get(pk=process_id, company=company)
            analytics_data = get_process_analytics(selected_process, company)
        except BusinessProcess.DoesNotExist:
            pass

    if compare_id:
        try:
            compare_process = BusinessProcess.objects.get(pk=compare_id, company=company)
            compare_data = get_process_analytics(compare_process, company)
        except BusinessProcess.DoesNotExist:
            pass

    return render(request, 'accounts/analytics_dashboard.html', {
        'processes': processes,
        'selected_process': selected_process,
        'analytics_data': analytics_data,
        'compare_process': compare_process,
        'compare_data': compare_data,
        'process_id': process_id,
        'compare_id': compare_id,
    })


def get_process_analytics(process, company):
    """Calculate all analytics for a given process using Composite Score method."""

    responses = EvaluationResponse.objects.filter(
        business_process=process
    )

    if not responses.exists():
        return None

    # ── Composite Satisfaction Score ──────────────────────────────
    # Step 1: Get average for each satisfaction category
    satisfaction_categories = [
        'system_quality',
        'information_quality',
        'process_efficiency',
        'user_satisfaction',
    ]

    category_avgs = []
    for cat in satisfaction_categories:
        avg = responses.filter(
            question__category=cat
        ).aggregate(avg=Avg('rating'))['avg']
        if avg:
            category_avgs.append(avg)

    # Step 2: Average of category averages
    overall_satisfaction = sum(category_avgs) / len(category_avgs) if category_avgs else 0

    # ── Perceived ROI Score ───────────────────────────────────────
    # ROI is measured separately — only Perceived ROI category
    roi_responses = responses.filter(question__category='perceived_roi')
    roi_score = roi_responses.aggregate(avg=Avg('rating'))['avg'] or 0

    # Participant count
    participant_count = responses.values('employee').distinct().count()

    # Category scores
    categories = [
        ('system_quality', 'System Quality'),
        ('information_quality', 'Information Quality'),
        ('process_efficiency', 'Process Efficiency'),
        ('user_satisfaction', 'User Satisfaction'),
        ('perceived_roi', 'Perceived ROI'),
    ]

    category_scores = {}
    for cat_key, cat_label in categories:
        avg = responses.filter(
            question__category=cat_key
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        category_scores[cat_label] = round(avg, 2)

    # Diagnosis — find issues (score < 3.0) per diagnosis tag
    diagnosis_issues = []
    diagnosis_tags = responses.values(
        'question__diagnosis_tag',
        'question__diagnosis_message',
        'question__category'
    ).annotate(avg=Avg('rating')).order_by('avg')

    for item in diagnosis_tags:
        tag = item['question__diagnosis_tag']
        message = item['question__diagnosis_message']
        avg = item['avg']
        category = item['question__category']
        if tag and avg:
            diagnosis_issues.append({
                'tag': tag,
                'message': message,
                'score': round(avg, 2),
                'category': category,
                'is_issue': avg < 3.0,
                'is_warning': 3.0 <= avg < 3.5,
            })

    # Sort — issues first
    diagnosis_issues.sort(key=lambda x: x['score'])

    # Category feedback comments
    feedbacks = CategoryFeedback.objects.filter(
        business_process=process
    ).order_by('-submitted_at')

    # Satisfaction classification
    if overall_satisfaction >= 4.0:
        satisfaction_class = 'High Satisfaction'
        satisfaction_color = 'success'
    elif overall_satisfaction >= 3.0:
        satisfaction_class = 'Moderate Satisfaction'
        satisfaction_color = 'warning'
    else:
        satisfaction_class = 'Low Satisfaction'
        satisfaction_color = 'danger'

    return {
        'overall_satisfaction': round(overall_satisfaction, 2),
        'roi_score': round(roi_score, 2),
        'participant_count': participant_count,
        'category_scores': category_scores,
        'diagnosis_issues': diagnosis_issues,
        'feedbacks': feedbacks,
        'satisfaction_class': satisfaction_class,
        'satisfaction_color': satisfaction_color,
        'category_labels': json.dumps(list(category_scores.keys())),
        'category_values': json.dumps(list(category_scores.values())),
    }

#report generation
@login_required
def download_report(request):
    if not request.user.is_admin():
        return redirect('accounts:login')

    company = request.user.company
    process_id = request.GET.get('process')
    compare_id = request.GET.get('compare')

    if not process_id:
        messages.error(request, 'Please select a process first.')
        return redirect('accounts:analytics_dashboard')

    try:
        selected_process = BusinessProcess.objects.get(pk=process_id, company=company)
    except BusinessProcess.DoesNotExist:
        messages.error(request, 'Process not found.')
        return redirect('accounts:analytics_dashboard')

    analytics_data = get_process_analytics(selected_process, company)

    if not analytics_data:
        messages.error(request, 'No evaluation data available for this process.')
        return redirect('accounts:analytics_dashboard')

    compare_process = None
    compare_data = None
    if compare_id:
        try:
            compare_process = BusinessProcess.objects.get(pk=compare_id, company=company)
            compare_data = get_process_analytics(compare_process, company)
        except BusinessProcess.DoesNotExist:
            pass

    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ERPInsight_Report_{selected_process.name}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4,
                           rightMargin=inch*0.75, leftMargin=inch*0.75,
                           topMargin=inch*0.75, bottomMargin=inch*0.75)

    styles = getSampleStyleSheet()
    purple = colors.HexColor('#7b1fa2')
    light_purple = colors.HexColor('#f3e5f5')
    dark_gray = colors.HexColor('#333333')

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=22, textColor=purple, spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=11, textColor=dark_gray, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
                                    fontSize=13, textColor=purple, spaceAfter=8, spaceBefore=15)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'],
                                   fontSize=10, textColor=dark_gray, spaceAfter=5)
    small_style = ParagraphStyle('Small', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.gray, spaceAfter=4)

    story = []

    # ── Header ────────────────────────────────────────────────────
    story.append(Paragraph("ERPInsight", title_style))
    story.append(Paragraph("ERP Business Process Evaluation Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=purple))
    story.append(Spacer(1, 12))

    # ── Report Info ───────────────────────────────────────────────
    from django.utils import timezone
    info_data = [
        ['Company', company.name],
        ['ERP Type', company.erp_type.upper()],
        ['Industry', company.industry.capitalize()],
        ['Business Process', selected_process.name],
        ['Report Generated', timezone.now().strftime('%d %B %Y, %I:%M %p')],
        ['Participants', str(analytics_data['participant_count'])],
    ]

    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), light_purple),
        ('TEXTCOLOR', (0,0), (0,-1), purple),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
        ('ROWBACKGROUNDS', (1,0), (1,-1), [colors.white]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # ── Score Summary ─────────────────────────────────────────────
    story.append(Paragraph("Score Summary", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
    story.append(Spacer(1, 8))

    score_data = [
        ['Metric', 'Score', 'Classification'],
        ['Overall Satisfaction Score',
         f"{analytics_data['overall_satisfaction']}/5",
         analytics_data['satisfaction_class']],
        ['Perceived ROI Score',
         f"{analytics_data['roi_score']}/5",
         'High' if analytics_data['roi_score'] >= 4.0 else 'Moderate' if analytics_data['roi_score'] >= 3.0 else 'Low'],
    ]

    score_table = Table(score_data, colWidths=[3*inch, 1.5*inch, 2*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), purple),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_purple]),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 15))

    # ── Category Scores ───────────────────────────────────────────
    story.append(Paragraph("Category Scores", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
    story.append(Spacer(1, 8))

    cat_data = [['Category', 'Average Score', 'Status']]
    for cat_name, score in analytics_data['category_scores'].items():
        if score >= 4.0:
            status = 'High'
        elif score >= 3.0:
            status = 'Moderate'
        else:
            status = 'Low'
        cat_data.append([cat_name, f"{score}/5", status])

    cat_table = Table(cat_data, colWidths=[3*inch, 1.5*inch, 2*inch])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), purple),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_purple]),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 15))

    # ── Issue Diagnosis ───────────────────────────────────────────
    story.append(Paragraph("Issue Diagnosis", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
    story.append(Spacer(1, 8))

    issues = [i for i in analytics_data['diagnosis_issues'] if i['is_issue'] or i['is_warning']]
    good = [i for i in analytics_data['diagnosis_issues'] if not i['is_issue'] and not i['is_warning']]

    if issues:
        story.append(Paragraph("⚠ Identified Issues & Warnings", normal_style))
        story.append(Spacer(1, 5))
        diag_data = [['Diagnosis Tag', 'Score', 'Issue Description']]
        for item in issues:
            diag_data.append([
                item['tag'],
                f"{item['score']}/5",
                item['message']
            ])
        diag_table = Table(diag_data, colWidths=[1.8*inch, 0.8*inch, 4*inch])
        diag_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dc3545')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fff5f5')]),
            ('WORDWRAP', (2,0), (2,-1), True),
        ]))
        story.append(diag_table)
        story.append(Spacer(1, 10))

    if good:
        story.append(Paragraph("✓ Areas Performing Well", normal_style))
        story.append(Spacer(1, 5))
        good_data = [['Diagnosis Tag', 'Score']]
        for item in good:
            good_data.append([item['tag'], f"{item['score']}/5"])
        good_table = Table(good_data, colWidths=[3*inch, 1.5*inch])
        good_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0fff4')]),
        ]))
        story.append(good_table)
        story.append(Spacer(1, 15))

    # ── Process Comparison ────────────────────────────────────────
    if compare_process and compare_data:
        story.append(Paragraph("Process Comparison", heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
        story.append(Spacer(1, 8))

        comp_data = [
            ['Metric', selected_process.name, compare_process.name],
            ['Satisfaction Score',
             f"{analytics_data['overall_satisfaction']}/5",
             f"{compare_data['overall_satisfaction']}/5"],
            ['ROI Score',
             f"{analytics_data['roi_score']}/5",
             f"{compare_data['roi_score']}/5"],
            ['Participants',
             str(analytics_data['participant_count']),
             str(compare_data['participant_count'])],
        ]
        for cat_name in analytics_data['category_scores']:
            comp_data.append([
                cat_name,
                f"{analytics_data['category_scores'].get(cat_name, 0)}/5",
                f"{compare_data['category_scores'].get(cat_name, 0)}/5",
            ])

        comp_table = Table(comp_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), purple),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('PADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lavender),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_purple]),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 15))

    # ── Employee Feedback ─────────────────────────────────────────
    if analytics_data['feedbacks']:
        story.append(Paragraph("Employee Feedback", heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
        story.append(Spacer(1, 8))

        for fb in analytics_data['feedbacks']:
            story.append(Paragraph(
                f"<b>{fb.category.replace('_', ' ').title()}</b> — {fb.submitted_at.strftime('%d %b %Y')}",
                small_style
            ))
            story.append(Paragraph(f'"{fb.feedback_text}"', normal_style))
            story.append(Spacer(1, 6))

    # ── Footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=light_purple))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by ERPInsight — ERP Business Process Evaluation System",
        small_style
    ))

    doc.build(story)
    return response

@login_required
def company_settings(request):
    if not request.user.is_super_admin():
        return redirect('accounts:login')
    company = request.user.company
    return render(request, 'accounts/company_settings.html', {'company': company})


@login_required
def edit_company(request):
    if not request.user.is_super_admin():
        return redirect('accounts:login')
    company = request.user.company
    if request.method == 'POST':
        company.name     = request.POST.get('name')
        company.industry = request.POST.get('industry')
        company.save()
        messages.success(request, 'Company details updated successfully!')
        return redirect('accounts:company_settings')
    return render(request, 'accounts/company_settings.html', {'company': company})

@login_required
def delete_company(request):
    if not request.user.is_super_admin():
        return redirect('accounts:login')
    if request.method == 'POST':
        company = request.user.company
        if company:
            company.delete()
            request.user.company = None
            request.user.save()
            messages.success(request, 'Company deleted successfully.')
        return redirect('accounts:super_admin_dashboard')
    return redirect('accounts:super_admin_dashboard')

@login_required
def super_admin_analytics(request):
    if not request.user.is_super_admin():
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')

    # Get the company registered by this super admin
    company = request.user.company
    processes = BusinessProcess.objects.filter(company=company, is_active=True) if company else []

    selected_process = None
    analytics_data = None
    compare_process = None
    compare_data = None

    process_id = request.GET.get('process')
    compare_id = request.GET.get('compare')

    if process_id:
        try:
            selected_process = BusinessProcess.objects.get(pk=process_id, company=company)
            analytics_data = get_process_analytics(selected_process, company)
        except BusinessProcess.DoesNotExist:
            pass

    if compare_id:
        try:
            compare_process = BusinessProcess.objects.get(pk=compare_id, company=company)
            compare_data = get_process_analytics(compare_process, company)
        except BusinessProcess.DoesNotExist:
            pass

    return render(request, 'accounts/super_admin_analytics.html', {
        'processes':        processes,
        'selected_process': selected_process,
        'analytics_data':   analytics_data,
        'compare_process':  compare_process,
        'compare_data':     compare_data,
        'process_id':       process_id,
        'compare_id':       compare_id,
        'company':          company,
    })