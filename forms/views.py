from django.shortcuts import render,redirect
from django.urls import path
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response 
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password,check_password
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone


from .models import *
from django.contrib import messages

# Create your views here.
def Homepage(Request):
    return HttpResponse("Home Page")
def Forms(Request):
    return HttpResponse("Form")
@api_view(['GET'])
def test_api(request):
    return Response({
        "message": "Django is connected to React!"
    })




def register_view(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        department = request.POST.get("department_name")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Check required fields
        if not name or not email or not department or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, "signup.html")

        # Check passwords
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        # Check existing email
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "signup.html")

        # Create user
        user = User(
            name=name,
            email=email,
            department=department,
            password=make_password(password),
          
        )

        user.save()

        messages.success(request, "Account created successfully.")

        return redirect("login")

    return render(request, "signup.html")
def settings_view(request):
    return render(request, "settings.html")

def login_view(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        # Check required fields
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "login.html")

        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        # Check password
        if not check_password(password, user.password):
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        # Store user information in session
        request.session["user_id"] = str(user.user_id)
        request.session["user_name"] = user.name
        request.session["user_email"] = user.email
        request.session["department"] = user.department

        # Remember meW
        if remember:
            # Session remains until browser closes or session expires
            request.session.set_expiry(1209600)  # 14 days
        else:
            # Session expires when browser is closed
            request.session.set_expiry(0)
        return redirect("forms_list")
        #return redirect("forms")

    # GET request → display login page
    return render(request, "login.html")
def forms_list_view(request):

    if "user_id" not in request.session:
        return redirect("login")

    forms = Form.objects.filter(
        owner__user_id=request.session["user_id"]
    ).order_by("-updated_at")

    context = {
        "user_name": request.session.get("user_name"),
        "forms": forms,
    }

    return render(request, "forms_list.html", context)
#def forms_view(request):
 #   if "user_id" not in request.session:
 #       return redirect("login")

  #  context = {
   #     "user_name": request.session.get("user_name"),
   # }

   # return render(request,"forms.html",context)
def forms_view(request, form_id=None):

    if "user_id" not in request.session:
        return redirect("login")

    form = None
    elements_json = "[]"

    if form_id:

        try:
            form = Form.objects.prefetch_related("elements__options").get(
                form_id=form_id,
                owner__user_id=request.session["user_id"]
            )
        except Form.DoesNotExist:
            return HttpResponse("Form not found.", status=404)

        elements_data = []

        for el in form.elements.order_by("order"):

            elements_data.append({
                "type": el.element_type,
                "id": str(el.element_id),
                "question": el.question_text,
                "questionType": el.question_type,
                "options": [opt.option_text for opt in el.options.all()],
                "required": el.is_required,
                "title": el.title,
                "description": el.description,
                "scaleMin": el.scale_min,
                "scaleMax": el.scale_max,
                "scaleMinLabel": el.scale_min_label,
                "scaleMaxLabel": el.scale_max_label,
                "gridRows": el.grid_rows.splitlines() if el.grid_rows else [],
                "maxFiles": el.max_files,
            })

        import json
        elements_json = json.dumps(elements_data)

    context = {
        "user_name": request.session.get("user_name"),
        "form": form,
        "elements_json": elements_json,
    }

    return render(request, "forms.html", context)
@transaction.atomic
def save_form(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        user = User.objects.get(user_id=request.session["user_id"])

        title = request.POST.get("title", "Untitled Form")
        description = request.POST.get("description", "")

        form = Form.objects.create(owner=user,owner_name=user.name, title=title, description=description)

        element_count = int(request.POST.get("element_count", 0))

        for index in range(element_count):

            element_type = request.POST.get(f"element_type_{index}")
            if not element_type:
                continue

            is_required = request.POST.get(f"is_required_{index}") == "true"

         
            element = FormElement.objects.create(
                form=form,
                order=index,
                element_type=element_type,
                is_required=is_required,
                question_text=request.POST.get(f"question_text_{index}", ""),
                question_type=request.POST.get(f"question_type_{index}", ""),
                title=request.POST.get(f"title_{index}", ""),
                description=request.POST.get(f"description_{index}", ""),
                image=request.FILES.get(f"image_{index}"),
                max_files=int(request.POST.get(f"max_files_{index}", 1) or 1),
                scale_min=request.POST.get(f"scale_min_{index}") or None,
                scale_max=request.POST.get(f"scale_max_{index}") or None,
                scale_min_label=request.POST.get(f"scale_min_label_{index}", ""),
                scale_max_label=request.POST.get(f"scale_max_label_{index}", ""),
                grid_rows=request.POST.get(f"grid_rows_{index}", ""),
)

            options = request.POST.getlist(f"options_{index}")
            for opt_index, option_text in enumerate(options):
                if option_text.strip():
                    ElementOption.objects.create(element=element, option_text=option_text, order=opt_index)

        return JsonResponse({"success": True, "message": "Form saved successfully.", "form_id": str(form.form_id)})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "User not found."}, status=404)

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@transaction.atomic
def publish_form(request, form_id):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return JsonResponse({"success": False, "message": "Form not found."}, status=404)

    action = request.POST.get("action", "publish")

    if action == "unpublish":
        form.is_published = False
        form.published_at = None
        form.save()
        return JsonResponse({"success": True, "is_published": False, "message": "Form unpublished."})

    form.is_published = True
    form.published_at = timezone.now()
    form.save()

    publish_link = request.build_absolute_uri(f"/f/{form.form_id}/")

    return JsonResponse({
        "success": True,
        "is_published": True,
        "publish_link": publish_link,
        "access_type": form.access_type,
        "message": "Form published."
    })


@transaction.atomic
def manage_access(request, form_id):

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return JsonResponse({"success": False, "message": "Form not found."}, status=404)

    # -------- GET: return current state to populate the modal --------
    if request.method == "GET":
        invites = list(form.invites.values("invite_id", "email").order_by("email"))
        for i in invites:
            i["invite_id"] = str(i["invite_id"])

        return JsonResponse({
            "success": True,
            "access_type": form.access_type,
            "invites": invites
        })

    # -------- POST: mutate access settings --------
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    action = request.POST.get("action")

    if action == "set_access_type":
        access_type = request.POST.get("access_type")

        if access_type not in ("anyone", "restricted"):
            return JsonResponse({"success": False, "message": "Invalid access type."}, status=400)

        form.access_type = access_type
        form.save()

        return JsonResponse({"success": True, "access_type": form.access_type})

    if action == "add_invite":
        email = (request.POST.get("email") or "").strip().lower()

        if not email:
            return JsonResponse({"success": False, "message": "Email is required."}, status=400)

        invite, created = FormInvite.objects.get_or_create(form=form, email=email)

        return JsonResponse({
            "success": True,
            "invite": {"invite_id": str(invite.invite_id), "email": invite.email}
        })

    if action == "remove_invite":
        invite_id = request.POST.get("invite_id")

        FormInvite.objects.filter(form=form, invite_id=invite_id).delete()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "message": "Unknown action."}, status=400)
def view_form(request, form_id):

    try:
        form = Form.objects.prefetch_related("elements__options").get(form_id=form_id)
    except Form.DoesNotExist:
        return render(request, "form_not_found.html", status=404)

    is_owner = "user_id" in request.session and str(form.owner.user_id) == request.session["user_id"]

    if not form.is_published and not is_owner:
        return render(request, "form_not_found.html", status=404)

    if form.access_type == "restricted" and not is_owner:
        viewer_email = request.session.get("user_email", "").strip().lower()
        if not form.invites.filter(email=viewer_email).exists():
            return render(request, "form_access_denied.html", status=403)
    elements = list(form.elements.order_by("order"))

    # Precompute the numeric range for linear-scale questions,
    # since Django templates can't build an arbitrary range on their own.
    for el in elements:
        if el.question_type == "linear_scale":
            lo = el.scale_min if el.scale_min is not None else 1
            hi = el.scale_max if el.scale_max is not None else 5
            el.scale_range = range(lo, hi + 1)

    return render(request, "public_form.html", {"form": form, "elements": elements})
def view_responses(request, form_id):

    if "user_id" not in request.session:
        return redirect("login")

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return HttpResponse("Form not found.", status=404)

    responses = form.responses.select_related("respondent").prefetch_related("answers__question").order_by("-submitted_at")

    elements = form.elements.filter(element_type="question").order_by("order")

    context = {
        "form": form,
        "responses": responses,
        "elements": elements,
        "response_count": responses.count(),
    }

    return render(request, "responses.html", context)
    #elements = form.elements.order_by("order")
    #for el in elements:
        #if el.question_type == "linear_scale":
            #el.scale_range = range(el.scale_min or 1, (el.scale_max or 5) + 1)

    #return render(request, "public_form.html", {"form": form, "elements": elements})