from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.core.mail import send_mail
import csv
from datetime import timedelta

from .models import User, Visitor, Visit, Notification, Blacklist
from .forms import LoginForm, VisitorForm, VisitForm, UserCreateForm, BlacklistForm
from .decorators import role_required


# ──────────────────────────────────────
# AUTH
# ──────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'],
                                password=form.cleaned_data['password'])
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ──────────────────────────────────────
# DASHBOARD ROUTER
# ──────────────────────────────────────
@login_required
def dashboard(request):
    role = request.user.role
    if role == 'admin' or request.user.is_superuser:
        return admin_dashboard(request)
    elif role == 'guard':
        return guard_dashboard(request)
    elif role == 'employee':
        return employee_dashboard(request)
    return redirect('login')


def admin_dashboard(request):
    today = timezone.now().date()
    total_visitors = Visitor.objects.count()
    today_visits = Visit.objects.filter(created_at__date=today).count()
    checked_in = Visit.objects.filter(status='checked_in').count()
    pending = Visit.objects.filter(status='pending').count()
    blacklisted = Blacklist.objects.count()
    total_users = User.objects.count()

    # Last 7 days chart data
    last_7 = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Visit.objects.filter(created_at__date=day).count()
        last_7.append({'date': day.strftime('%b %d'), 'count': count})

    recent_visits = Visit.objects.select_related('visitor', 'host').all()[:10]

    context = {
        'total_visitors': total_visitors,
        'today_visits': today_visits,
        'checked_in': checked_in,
        'pending': pending,
        'blacklisted': blacklisted,
        'total_users': total_users,
        'chart_labels': [d['date'] for d in last_7],
        'chart_data': [d['count'] for d in last_7],
        'recent_visits': recent_visits,
    }
    return render(request, 'dashboard_admin.html', context)


def guard_dashboard(request):
    today = timezone.now().date()
    today_visits = Visit.objects.filter(created_at__date=today).select_related('visitor', 'host')
    checked_in = today_visits.filter(status='checked_in').count()
    checked_out = today_visits.filter(status='checked_out').count()
    pending = today_visits.filter(status='pending').count()
    approved = today_visits.filter(status='approved').count()

    context = {
        'today_visits': today_visits[:20],
        'checked_in': checked_in,
        'checked_out': checked_out,
        'pending': pending,
        'approved': approved,
    }
    return render(request, 'dashboard_guard.html', context)


def employee_dashboard(request):
    pending_visits = Visit.objects.filter(host=request.user, status='pending').select_related('visitor')
    my_visits = Visit.objects.filter(host=request.user).exclude(status='pending').select_related('visitor')[:20]
    notifications = Notification.objects.filter(user=request.user)[:10]

    context = {
        'pending_visits': pending_visits,
        'my_visits': my_visits,
        'notifications': notifications,
    }
    return render(request, 'dashboard_employee.html', context)


# ──────────────────────────────────────
# VISITOR REGISTRATION
# ──────────────────────────────────────
@login_required
@role_required('guard', 'admin')
def register_visitor(request):
    visitor_form = VisitorForm()
    visit_form = VisitForm()

    if request.method == 'POST':
        visitor_form = VisitorForm(request.POST, request.FILES)
        visit_form = VisitForm(request.POST)

        if visitor_form.is_valid() and visit_form.is_valid():
            # Check blacklist
            phone = visitor_form.cleaned_data['phone']
            blacklisted = Blacklist.objects.filter(visitor__phone=phone).exists()
            if blacklisted:
                messages.error(request, '⛔ This visitor is BLACKLISTED and cannot be registered.')
                return render(request, 'register_visitor.html',
                              {'visitor_form': visitor_form, 'visit_form': visit_form})

            visitor = visitor_form.save(commit=False)
            visitor.created_by = request.user
            visitor.save()

            visit = visit_form.save(commit=False)
            visit.visitor = visitor
            visit.save()

            # Notify host
            if visit.host:
                Notification.objects.create(
                    user=visit.host,
                    visit=visit,
                    message=f'Visitor "{visitor.name}" from {visitor.company or "N/A"} is here to see you. Purpose: {visit.purpose}'
                )
                try:
                    send_mail(
                        subject=f'Visitor Alert: {visitor.name}',
                        message=f'{visitor.name} from {visitor.company or "N/A"} has arrived. Purpose: {visit.purpose}. Please approve from your dashboard.',
                        from_email='vms@company.com',
                        recipient_list=[visit.host.email] if visit.host.email else [],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            messages.success(request, f'✅ Visitor "{visitor.name}" registered successfully! Host notified.')
            return redirect('dashboard')

    return render(request, 'register_visitor.html', {'visitor_form': visitor_form, 'visit_form': visit_form})


# ──────────────────────────────────────
# CHECK-IN / CHECK-OUT
# ──────────────────────────────────────
@login_required
@role_required('guard', 'admin')
def check_in(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)
    if visit.status not in ('approved', 'pending'):
        messages.warning(request, 'This visit cannot be checked in.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
    visit.status = 'checked_in'
    visit.check_in = timezone.now()
    visit.save()
    messages.success(request, f'✅ {visit.visitor.name} checked in at {visit.check_in.strftime("%I:%M %p")}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
@role_required('guard', 'admin')
def check_out(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)
    if visit.status != 'checked_in':
        messages.warning(request, 'This visit cannot be checked out.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
    visit.status = 'checked_out'
    visit.check_out = timezone.now()
    visit.save()
    messages.success(request, f'✅ {visit.visitor.name} checked out. Duration: {visit.duration}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ──────────────────────────────────────
# EMPLOYEE: APPROVE / REJECT
# ──────────────────────────────────────
@login_required
@role_required('employee', 'admin')
def approve_visit(request, visit_id):
    if request.user.role == 'admin' or request.user.is_superuser:
        visit = get_object_or_404(Visit, id=visit_id)
    else:
        visit = get_object_or_404(Visit, id=visit_id, host=request.user)
    visit.status = 'approved'
    visit.save()
    messages.success(request, f'✅ Visit from {visit.visitor.name} approved.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
@role_required('employee', 'admin')
def reject_visit(request, visit_id):
    if request.user.role == 'admin' or request.user.is_superuser:
        visit = get_object_or_404(Visit, id=visit_id)
    else:
        visit = get_object_or_404(Visit, id=visit_id, host=request.user)
    visit.status = 'rejected'
    visit.save()
    messages.info(request, f'❌ Visit from {visit.visitor.name} rejected.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ──────────────────────────────────────
# VISITOR HISTORY
# ──────────────────────────────────────
@login_required
def visitor_history(request):
    visits = Visit.objects.select_related('visitor', 'host').all()
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if q:
        visits = visits.filter(
            Q(visitor__name__icontains=q) | Q(visitor__phone__icontains=q) |
            Q(host__first_name__icontains=q) | Q(host__last_name__icontains=q) |
            Q(purpose__icontains=q)
        )
    if status:
        visits = visits.filter(status=status)
    if date_from:
        visits = visits.filter(created_at__date__gte=date_from)
    if date_to:
        visits = visits.filter(created_at__date__lte=date_to)

    # Export CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visitor_history.csv"'
        writer = csv.writer(response)
        writer.writerow(['Visitor', 'Phone', 'Company', 'Host', 'Purpose', 'Status', 'Check In', 'Check Out', 'Duration'])
        for v in visits:
            writer.writerow([
                v.visitor.name, v.visitor.phone, v.visitor.company or '',
                v.host.get_full_name() if v.host else '', v.purpose,
                v.get_status_display(),
                v.check_in.strftime('%Y-%m-%d %H:%M') if v.check_in else '',
                v.check_out.strftime('%Y-%m-%d %H:%M') if v.check_out else '',
                v.duration or '',
            ])
        return response

    context = {
        'visits': visits[:100],
        'q': q, 'status': status, 'date_from': date_from, 'date_to': date_to,
        'status_choices': Visit.STATUS_CHOICES,
    }
    return render(request, 'visitor_history.html', context)


# ──────────────────────────────────────
# VISITOR LIST
# ──────────────────────────────────────
@login_required
def visitor_list(request):
    visitors = Visitor.objects.all()
    q = request.GET.get('q', '')
    if q:
        visitors = visitors.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q)
        )
    return render(request, 'visitor_list.html', {'visitors': visitors[:100], 'q': q})


# ──────────────────────────────────────
# MANAGE USERS (ADMIN)
# ──────────────────────────────────────
@login_required
@role_required('admin')
def manage_users(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'manage_users.html', {'users': users})


@login_required
@role_required('admin')
def create_user(request):
    form = UserCreateForm()
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ User created successfully!')
            return redirect('manage_users')
    return render(request, 'create_user.html', {'form': form})


@login_required
@role_required('admin')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
    else:
        user.delete()
        messages.success(request, f'User "{user.username}" deleted.')
    return redirect('manage_users')


# ──────────────────────────────────────
# BLACKLIST MANAGEMENT
# ──────────────────────────────────────
@login_required
@role_required('admin')
def blacklist_management(request):
    blacklisted = Blacklist.objects.select_related('visitor', 'blacklisted_by').all()
    return render(request, 'blacklist.html', {'blacklisted': blacklisted})


@login_required
@role_required('admin')
def blacklist_visitor(request, visitor_id):
    visitor = get_object_or_404(Visitor, id=visitor_id)
    if hasattr(visitor, 'blacklist_entry'):
        messages.warning(request, 'Visitor is already blacklisted.')
        return redirect('blacklist_management')

    form = BlacklistForm()
    if request.method == 'POST':
        form = BlacklistForm(request.POST)
        if form.is_valid():
            bl = form.save(commit=False)
            bl.visitor = visitor
            bl.blacklisted_by = request.user
            bl.save()
            messages.success(request, f'⛔ {visitor.name} has been blacklisted.')
            return redirect('blacklist_management')
    return render(request, 'blacklist_add.html', {'form': form, 'visitor': visitor})


@login_required
@role_required('admin')
def remove_blacklist(request, blacklist_id):
    bl = get_object_or_404(Blacklist, id=blacklist_id)
    name = bl.visitor.name
    bl.delete()
    messages.success(request, f'✅ {name} removed from blacklist.')
    return redirect('blacklist_management')


# ──────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifications': notifs[:50]})


# ──────────────────────────────────────
# REPORTS
# ──────────────────────────────────────
@login_required
@role_required('admin')
def reports(request):
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())

    visits = Visit.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    total = visits.count()
    approved = visits.filter(status__in=['approved', 'checked_in', 'checked_out']).count()
    rejected = visits.filter(status='rejected').count()
    checked_out = visits.filter(status='checked_out').count()

    # Daily breakdown
    daily = visits.annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')

    # Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Visit Count'])
        for d in daily:
            writer.writerow([d['date'].strftime('%Y-%m-%d'), d['count']])
        writer.writerow([])
        writer.writerow(['Total', total])
        writer.writerow(['Approved', approved])
        writer.writerow(['Rejected', rejected])
        writer.writerow(['Checked Out', checked_out])
        return response

    context = {
        'date_from': date_from, 'date_to': date_to,
        'total': total, 'approved': approved, 'rejected': rejected, 'checked_out': checked_out,
        'daily_labels': [d['date'].strftime('%b %d') for d in daily],
        'daily_data': [d['count'] for d in daily],
    }
    return render(request, 'reports.html', context)
