import hashlib
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Application,NameReservation, Payment, SystemFee,CompanyDetails,CompanyDirector,CompanyShareholder
from django.template.loader import render_to_string
from django.http import FileResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from weasyprint import HTML 
import uuid
from django.db.models import Q
from django.utils import timezone



# ============================================================
# NAME RESERVATION
# ============================================================

def normalize_business_name(name):
    """
    Normalize a proposed business name so that differences
    in capitalization or extra spaces cannot bypass checking.
    """
    return " ".join(
        (name or "").strip().upper().split()
    )


def is_name_available(name, exclude_reservation=None):
    """
    Check whether a business name is available.

    A name is unavailable if:
    1. It has already been officially reserved.
    2. It belongs to an approved application.

    Payment-submitted reservations do NOT permanently block
    the name until staff confirms the payment.
    """

    name = normalize_business_name(name)

    if not name:
        return False

    # Check officially reserved names
    reservation_query = NameReservation.objects.filter(
        proposed_name=name,
        status=NameReservation.Status.RESERVED
    )

    if exclude_reservation:
        reservation_query = reservation_query.exclude(
            pk=exclude_reservation.pk
        )

    if reservation_query.exists():
        return False

    # Check names already used by approved applications
    approved_application = Application.objects.filter(
        status=Application.Status.APPROVED
    ).filter(
        Q(proposed_name_1=name) |
        Q(proposed_name_2=name)
    ).exists()

    if approved_application:
        return False

    return True



@login_required
@require_http_methods(["GET", "POST"])
def name_reservation(request):
    reservations = NameReservation.objects.filter(
        user=request.user
    ).order_by("-created_at")

    context = {
        "reservations": reservations,
        "available": None,
        "checked_name": "",
        "reservation_fee": None,
        "registration_type":"",
    }

    # Open the reservation page
    if request.method == "GET":
        return render(
            request,
            "applications/name_reservation.html",
            context
        )

    # Get submitted values
    action = request.POST.get("action", "").strip()
    proposed_name = normalize_business_name(
        request.POST.get("proposed_name", "")
    )
    registration_type = request.POST.get(
        "registration_type",
        ""
    ).strip()

    # ============================================================
    # VALIDATE REGISTRATION TYPE
    # ============================================================

    valid_registration_types = [
        NameReservation.RegistrationType.BUSINESS,
        NameReservation.RegistrationType.COMPANY,
    ]

    if registration_type not in valid_registration_types:

        messages.error(
            request,
            "Please select whether you want to register a Business Name or Company."
        )

        return redirect(
            "applications:name_reservation"
        )

    # -----------------------------------------
    # CHECK NAME AVAILABILITY
    # -----------------------------------------
    if action == "check":

        if not proposed_name:
            messages.error(
                request,
                "Please enter a proposed business/company name."
            )
            return redirect("applications:name_reservation")

        available = is_name_available(proposed_name)

        context["available"] = available
        context["checked_name"] = proposed_name
        context["registration_type"] = registration_type

        if available:

            system_fee = SystemFee.objects.first()

            if not system_fee:
                messages.error(
                    request,
                    "The reservation fee has not been configured."
                )
                return redirect("applications:name_reservation")

            context["reservation_fee"] = system_fee.name_reservation_fee

        else:
            messages.error(
                request,
                f'"{proposed_name}" is not available.'
            )

        return render(
            request,
            "applications/name_reservation.html",
            context
        )

    # -----------------------------------------
    # CREATE RESERVATION
    # -----------------------------------------
    elif action == "reserve":

        if not proposed_name:
            messages.error(
                request,
                "Please enter a proposed business/company name."
            )
            return redirect("applications:name_reservation")

        # Check again because another user could have
        # reserved the name after the first search.
        if not is_name_available(proposed_name):
            messages.error(
                request,
                f'"{proposed_name}" is no longer available.'
            )
            return redirect("applications:name_reservation")

        system_fee = SystemFee.objects.first()

        if not system_fee:
            messages.error(
                request,
                "The reservation fee has not been configured."
            )
            return redirect("applications:name_reservation")

        fee = system_fee.name_reservation_fee

        if fee <= 0:
            messages.error(
                request,
                "The reservation fee has not been properly configured."
            )
            return redirect("applications:name_reservation")

        reservation = NameReservation.objects.create(
            user=request.user,
            proposed_name=proposed_name,
            # NEW:
            # Save whether this reservation is for a
            # Business Name or Company.
            registration_type=registration_type,
            reservation_fee=fee,
            status=NameReservation.Status.AWAITING_PAYMENT
        )
        # Get a readable label for the success message
        registration_type_label = (
            reservation.get_registration_type_display()
        )

        messages.success(
            request,
            f"{registration_type_label} name reservation created. "
            f"Please proceed to payment. "
            f"The name will only become officially reserved after your payment is confirmed by CAC staff."
        )

        return redirect(
            "applications:reservation_payment",
            reference_id=reservation.reference_id
        )

    # -----------------------------------------
    # INVALID ACTION
    # -----------------------------------------
    else:
        messages.error(
            request,
            "Invalid reservation request."
        )

        return redirect(
            "applications:name_reservation"
        )



# ------------------------------------------------------------
# SIMULATED NAME RESERVATION PAYMENT
# ------------------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def reservation_payment(request, reference_id):

    reservation = get_object_or_404(
        NameReservation,
        reference_id=reference_id,
        user=request.user
    )

    # Prevent paying again after payment has already been
    # submitted or the name has already been reserved.
    if reservation.status == NameReservation.Status.RESERVED:
        messages.info(
            request,
            "This name has already been reserved."
        )
        return redirect("dashboard:home")

    if reservation.status == NameReservation.Status.PAYMENT_SUBMITTED:
        messages.info(
            request,
            "Payment has already been submitted and is awaiting staff confirmation."
        )
        return redirect("dashboard:home")

    if reservation.status != NameReservation.Status.AWAITING_PAYMENT:
        messages.error(
            request,
            "This reservation is not available for payment."
        )
        return redirect("dashboard:home")

    if request.method == "GET":
        return render(
            request,
            "applications/reservation-payment.html",
            {
                "reservation": reservation
            }
        )

    # --------------------------------------------------------
    # SIMULATED PAYMENT SUBMISSION
    # --------------------------------------------------------

    payment_reference = (
        "SIM-NR-" +
        uuid.uuid4().hex[:12].upper()
    )

    payment = Payment.objects.create(
        user=request.user,
        payment_type=Payment.PaymentType.NAME_RESERVATION,
        reservation=reservation,
        amount=reservation.reservation_fee,
        payment_reference=payment_reference,
        status=Payment.Status.SUBMITTED,
        submitted_at=timezone.now()
    )

    reservation.payment_reference = payment_reference
    reservation.payment_submitted_at = timezone.now()
    reservation.status = NameReservation.Status.PAYMENT_SUBMITTED
    reservation.save(
        update_fields=[
            "payment_reference",
            "payment_submitted_at",
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Payment submitted successfully. "
        "Your name will only become officially reserved after staff confirms the payment."
    )

    return redirect("applications:reservation_payment_status",reference_id=reservation.reference_id)




@login_required
@require_http_methods(["GET"])
def reservation_payment_status(request, reference_id):
    reservation = get_object_or_404(
    NameReservation,
    reference_id=reference_id,
    user=request.user
    )


    payment = Payment.objects.filter(
        reservation=reservation,
        payment_type=Payment.PaymentType.NAME_RESERVATION
    ).order_by("-created_at").first()

    if not payment:
        messages.info(
            request,
            "No payment has been submitted for this reservation yet."
        )
        return redirect(
            "applications:reservation_payment",
            reference_id=reservation.reference_id
        )

    return render(
        request,
        "applications/reservation-payment-status.html",
        {
            "reservation": reservation,
            "payment": payment,
        }
    )

# ------------------------------------------------------------
# SIMULATED APPLICATION PAYMENT
# ------------------------------------------------------------
@login_required
@require_http_methods(["GET", "POST"])
def application_payment(request, reference_id):
    application = get_object_or_404(
        Application,
        reference_id=reference_id,
        user=request.user
    )

    # Get the application fee
    system_fee = SystemFee.objects.first()

    if not system_fee:
        messages.error(
            request,
            "The application fee has not been configured."
        )
        return redirect("dashboard:home")

    application_fee = system_fee.application_fee

    if application_fee <= 0:
        messages.error(
            request,
            "The application fee has not been properly configured."
        )
        return redirect("dashboard:home")

    # Get the latest application payment
    existing_payment = Payment.objects.filter(
        application=application,
        payment_type=Payment.PaymentType.APPLICATION
    ).order_by("-created_at").first()

    # --------------------------------------------------------
    # PAYMENT ALREADY CONFIRMED
    # --------------------------------------------------------
    if existing_payment and existing_payment.status == Payment.Status.CONFIRMED:
        messages.info(
            request,
            "Payment for this application has already been confirmed."
        )
        return redirect("dashboard:home")

    # --------------------------------------------------------
    # PAYMENT ALREADY SUBMITTED
    # --------------------------------------------------------
    if existing_payment and existing_payment.status == Payment.Status.SUBMITTED:
        messages.info(
            request,
            "Payment has already been submitted and is awaiting staff confirmation."
        )
        return redirect(
            "applications:application_payment_status",
            reference_id=application.reference_id
        )

    # --------------------------------------------------------
    # SHOW PAYMENT PAGE
    # --------------------------------------------------------
    if request.method == "GET":
        return render(
            request,
            "applications/application-payment.html",
            {
                "application": application,
                "application_fee": application_fee,
                "payment": existing_payment,
            }
        )

    # --------------------------------------------------------
    # SIMULATED PAYMENT SUBMISSION
    # --------------------------------------------------------

    if existing_payment:
        # Change the existing PENDING payment to SUBMITTED
        existing_payment.status = Payment.Status.SUBMITTED
        existing_payment.submitted_at = timezone.now()
        existing_payment.amount = application_fee

        if not existing_payment.payment_reference:
            existing_payment.payment_reference = (
                "SIM-APP-" +
                uuid.uuid4().hex[:12].upper()
            )

        existing_payment.save()

        payment = existing_payment

    else:
        # Create a payment only if one does not already exist
        payment_reference = (
            "SIM-APP-" +
            uuid.uuid4().hex[:12].upper()
        )

        payment = Payment.objects.create(
            user=request.user,
            payment_type=Payment.PaymentType.APPLICATION,
            application=application,
            amount=application_fee,
            payment_reference=payment_reference,
            status=Payment.Status.SUBMITTED,
            submitted_at=timezone.now()
        )


    return redirect(
        "applications:application_payment_status",
        reference_id=application.reference_id
    )

@login_required
@require_http_methods(["GET"])
def application_payment_status(request, reference_id):

    application = get_object_or_404(
        Application,
        reference_id=reference_id,
        user=request.user
    )

    payment = Payment.objects.filter(
        application=application,
        payment_type=Payment.PaymentType.APPLICATION
    ).order_by("-created_at").first()

    if not payment:
        messages.info(
            request,
            "No payment has been submitted for this application yet."
        )

        return redirect(
            "applications:application_payment",
            reference_id=application.reference_id
        )

    return render(
        request,
        "applications/application-payment-status.html",
        {
            "application": application,
            "payment": payment,
        }
    )

# ============================================================
# START BUSINESS REGISTRATION APPLICATION
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def start_application(request):

    # ------------------------------------------------------------
    # GET THE USER'S LATEST CONFIRMED NAME RESERVATION
    # ------------------------------------------------------------

    confirmed_reservation = (
        NameReservation.objects
        .filter(
            user=request.user,
            status=NameReservation.Status.RESERVED,
            application__isnull=True
        )
        .order_by("-confirmed_at")
        .first()
    )

    # A user cannot start an application without a confirmed name
    if not confirmed_reservation:
        messages.error(
            request,
            "You must have a confirmed Business/Company name reservation before starting an application."
        )
        return redirect("applications:name_reservation")

    # ------------------------------------------------------------ 
    # # CHECK REGISTRATION TYPE 
    # # ------------------------------------------------------------ 
    if confirmed_reservation.registration_type == NameReservation.RegistrationType.COMPANY:
        return redirect("applications:company_start")

    # ------------------------------------------------------------
    # GET REQUEST - Business name
    # ------------------------------------------------------------

    if request.method == "GET":
        return render(
            request,
            "applications/application.html",
            {
                "confirmed_reservation": confirmed_reservation
            }
        )

    # ------------------------------------------------------------
    # FORM DATA
    # ------------------------------------------------------------

    # Option 1 MUST come from the confirmed reservation.
    # We do NOT trust the value submitted by the browser.
    proposed_name_1 = normalize_business_name(
        confirmed_reservation.proposed_name
    )

    proposed_name_2 = normalize_business_name(
        request.POST.get("proposed_name_2", "")
    )

    nature_of_business = (
        request.POST.get("nature_of_business") or ""
    ).strip()

    business_type = (
        request.POST.get("business_type") or ""
    ).strip()

    state = (
        request.POST.get("state") or ""
    ).strip().upper()

    lga = (
        request.POST.get("lga") or ""
    ).strip().upper()

    business_address = (
        request.POST.get("business_address") or ""
    ).strip().upper()

    owner_first_name = (
        request.POST.get("owner_first_name") or ""
    ).strip()

    owner_last_name = (
        request.POST.get("owner_last_name") or ""
    ).strip()

    owner_email = (
        request.POST.get("owner_email") or ""
    ).strip()

    owner_phone = (
        request.POST.get("owner_phone") or ""
    ).strip()

    business_description = (
        request.POST.get("business_description") or ""
    ).strip()

    confirm = request.POST.get("confirm")

    passport = request.FILES.get("passport")
    signature = request.FILES.get("signature")
    nin = request.FILES.get("nin")

    save_as_draft = request.POST.get("save_as_draft") == "1"

    # ------------------------------------------------------------
    # RECHECK RESERVATION BEFORE CREATING APPLICATION
    # ------------------------------------------------------------

    confirmed_reservation.refresh_from_db()

    if confirmed_reservation.status != NameReservation.Status.RESERVED:
        messages.error(
            request,
            "Your business/company name reservation is no longer confirmed. "
            "Please check your name reservation status."
        )
        return redirect("applications:name_reservation")

    # ------------------------------------------------------------
    # PREVENT ONE RESERVATION FROM BEING USED TWICE
    # ------------------------------------------------------------

    existing_application = Application.objects.filter(
        name_reservation=confirmed_reservation
    ).first()

    if existing_application:
        messages.info(
            request,
            f"This reserved business name has already been used for application "
            f"{existing_application.reference_id}."
        )
        return redirect("dashboard:home")

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    errors = []

    if not save_as_draft:

        if not proposed_name_1:
            errors.append(
                "Your confirmed business name is required."
            )

        if not nature_of_business:
            errors.append(
                "Nature of Business is required."
            )

        if not business_type:
            errors.append(
                "Business Type is required."
            )

        if not state:
            errors.append(
                "State is required."
            )

        if not lga:
            errors.append(
                "LGA is required."
            )

        if not business_address:
            errors.append(
                "Business Address is required."
            )

        if not owner_first_name:
            errors.append(
                "Owner First Name is required."
            )

        if not owner_last_name:
            errors.append(
                "Owner Last Name is required."
            )

        if not owner_email:
            errors.append(
                "Owner Email is required."
            )

        if not owner_phone:
            errors.append(
                "Owner Phone is required."
            )

        if not passport:
            errors.append(
                "Passport Photograph is required."
            )

        if not signature:
            errors.append(
                "Signature is required."
            )

        if not nin:
            errors.append(
                "NIN Slip is required."
            )

        if not confirm:
            errors.append(
                "You must confirm that the information is correct."
            )

    if errors:
        for error in errors:
            messages.error(request, error)

        return render(
            request,
            "applications/application.html",
            {
                "confirmed_reservation": confirmed_reservation
            }
        )

    # ------------------------------------------------------------
    # GET APPLICATION FEE
    # ------------------------------------------------------------

    system_fee = SystemFee.objects.first()

    if not system_fee:
        messages.error(
            request,
            "The application fee has not been configured."
        )
        return redirect("dashboard:home")

    application_fee = system_fee.application_fee

    if not application_fee or application_fee <= 0:
        messages.error(
            request,
            "The application fee has not been properly configured."
        )
        return redirect("dashboard:home")

    # ------------------------------------------------------------
    # CREATE APPLICATION
    # ------------------------------------------------------------

    if save_as_draft:
        status = Application.Status.PENDING
    else:
        status = Application.Status.SUBMITTED

    app = Application.objects.create(
        user=request.user,

        # Link application to the officially reserved name
        name_reservation=confirmed_reservation,

        # Option 1 comes ONLY from confirmed reservation
        proposed_name_1=proposed_name_1,

        # Option 2 is optional
        proposed_name_2=proposed_name_2,

        nature_of_business=nature_of_business,
        business_type=business_type,

        state=state,
        lga=lga,
        business_address=business_address,

        owner_first_name=owner_first_name,
        owner_last_name=owner_last_name,
        owner_email=owner_email,
        owner_phone=owner_phone,

        business_description=business_description,

        passport=passport,
        signature=signature,
        nin=nin,

        status=status
    )

    # ------------------------------------------------------------
    # DRAFT
    # ------------------------------------------------------------

    if save_as_draft:

        messages.success(
            request,
            f"Draft saved successfully. Ref: {app.reference_id}"
        )

        return redirect("dashboard:home")

    # ------------------------------------------------------------
    # CREATE APPLICATION PAYMENT
    # ------------------------------------------------------------

    payment_reference = (
        "SIM-APP-" +
        uuid.uuid4().hex[:12].upper()
    )

    Payment.objects.create(
        user=request.user,
        payment_type=Payment.PaymentType.APPLICATION,
        application=app,
        amount=application_fee,
        payment_reference=payment_reference,
        status=Payment.Status.PENDING
    )


    # ------------------------------------------------------------
    # SEND USER TO APPLICATION PAYMENT
    # ------------------------------------------------------------

    return redirect(
        "applications:application_payment",
        reference_id=app.reference_id
    )


@login_required
def company_start_application(request):
    """
    Create a new Company registration application
    from a confirmed Company name reservation.
    """

    confirmed_reservation = (
        NameReservation.objects
        .filter(
            user=request.user,
            status=NameReservation.Status.RESERVED,
            registration_type=NameReservation.RegistrationType.COMPANY,
            application__isnull=True
        )
        .order_by("-confirmed_at")
        .first()
    )

    if not confirmed_reservation:
        messages.error(
            request,
            "You do not have a confirmed Company name reservation available."
        )
        return redirect("applications:name_reservation")


    # -----------------------------
    # GET
    # -----------------------------
    if request.method == "GET":
        return render(
            request,
            "applications/company_application.html",
            {
                "confirmed_reservation": confirmed_reservation,
            }
        )


    # -----------------------------
    # POST
    # -----------------------------
    proposed_name_1 = normalize_business_name(
        request.POST.get("proposed_name_1")
    )

    principal_business_activity = (
        request.POST.get("principal_business_activity") or ""
    ).strip()

    company_type = (
        request.POST.get("company_type") or ""
    ).strip()

    state = normalize_business_name(
        request.POST.get("state")
    )

    lga = normalize_business_name(
        request.POST.get("lga")
    )

    business_address = normalize_business_name(
        request.POST.get("business_address")
    )

    company_email = (
        request.POST.get("company_email") or ""
    ).strip()

    company_phone = (
        request.POST.get("company_phone") or ""
    ).strip()

    business_description = (
        request.POST.get("business_description") or ""
    ).strip()


    passport = request.FILES.get("passport")
    signature = request.FILES.get("signature")
    nin = request.FILES.get("nin")


    # -----------------------------
    # Basic validation
    # -----------------------------
    if not proposed_name_1:
        messages.error(
            request,
            "The confirmed Company name is required."
        )
        return redirect("applications:company_start")


    if proposed_name_1 != normalize_business_name(
        confirmed_reservation.proposed_name
    ):
        messages.error(
            request,
            "The Company name does not match the confirmed reservation."
        )
        return redirect("applications:company_start")


    if not company_type:
        messages.error(
            request,
            "Please select a Company type."
        )
        return redirect("applications:company_start")


    if not principal_business_activity:
        messages.error(
            request,
            "Principal business activity is required."
        )
        return redirect("applications:company_start")


    if not state or not lga:
        messages.error(
            request,
            "State and LGA are required."
        )
        return redirect("applications:company_start")


    if not business_address:
        messages.error(
            request,
            "Registered office address is required."
        )
        return redirect("applications:company_start")


    if not company_email:
        messages.error(
            request,
            "Company email is required."
        )
        return redirect("applications:company_start")


    if not company_phone:
        messages.error(
            request,
            "Company phone is required."
        )
        return redirect("applications:company_start")


    if not passport or not signature or not nin:
        messages.error(
            request,
            "Passport, Signature and NIN are required."
        )
        return redirect("applications:company_start")


    # -----------------------------
    # Get directors
    # -----------------------------
    director_first_names = request.POST.getlist(
        "director_first_name[]"
    )

    director_last_names = request.POST.getlist(
        "director_last_name[]"
    )

    director_emails = request.POST.getlist(
        "director_email[]"
    )

    director_phones = request.POST.getlist(
        "director_phone[]"
    )

    director_addresses = request.POST.getlist(
        "director_address[]"
    )

    director_dates_of_birth = request.POST.getlist(
        "director_date_of_birth[]"
    )

    director_nationalities = request.POST.getlist(
        "director_nationality[]"
    )


    # -----------------------------
    # Validate directors
    # -----------------------------
    director_count = len(director_first_names)

    if director_count == 0:
        messages.error(
            request,
            "At least one Director is required."
        )
        return redirect("applications:company_start")


    if not (
        len(director_last_names)
        == len(director_emails)
        == len(director_phones)
        == len(director_addresses)
        == len(director_dates_of_birth)
        == len(director_nationalities)
        == director_count
    ):
        messages.error(
            request,
            "Please complete all Director information."
        )
        return redirect("applications:company_start")


    # -----------------------------
    # Get shareholders
    # -----------------------------
    shareholder_names = request.POST.getlist(
        "shareholder_full_name[]"
    )

    shareholder_emails = request.POST.getlist(
        "shareholder_email[]"
    )

    shareholder_phones = request.POST.getlist(
        "shareholder_phone[]"
    )

    shareholder_shares = request.POST.getlist(
        "shareholder_number_of_shares[]"
    )

    shareholder_percentages = request.POST.getlist(
        "shareholder_shareholding_percentage[]"
    )


    # -----------------------------
    # Validate shareholders
    # -----------------------------
    shareholder_count = len(shareholder_names)

    if shareholder_count == 0:
        messages.error(
            request,
            "At least one Shareholder is required."
        )
        return redirect("applications:company_start")


    if not (
        len(shareholder_emails)
        == len(shareholder_phones)
        == len(shareholder_shares)
        == len(shareholder_percentages)
        == shareholder_count
    ):
        messages.error(
            request,
            "Please complete all Shareholder information."
        )
        return redirect("applications:company_start")


    # -----------------------------
    # Prevent reservation reuse
    # -----------------------------
    if Application.objects.filter(
        name_reservation=confirmed_reservation
    ).exists():
        messages.error(
            request,
            "This Company name reservation has already been used."
        )
        return redirect("applications:company_start")


    # -----------------------------
    # Get application fee
    # -----------------------------
    system_fee = SystemFee.objects.first()

    if not system_fee:
        messages.error(
            request,
            "Application fee has not been configured."
        )
        return redirect("applications:company_start")


    # -----------------------------
    # Save as draft?
    # -----------------------------
    save_as_draft = (
        request.POST.get("save_as_draft") == "1"
    )


    # -----------------------------
    # Create Application
    # -----------------------------
    application = Application.objects.create(
        user=request.user,
        name_reservation=confirmed_reservation,
        registration_type=Application.RegistrationType.COMPANY,

        proposed_name_1=proposed_name_1,
        proposed_name_2="",

        nature_of_business=principal_business_activity,
        business_type=company_type,

        state=state,
        lga=lga,
        business_address=business_address,

        owner_first_name="",
        owner_last_name="",
        owner_email=company_email,
        owner_phone=company_phone,

        business_description=business_description,

        passport=passport,
        signature=signature,
        nin=nin,

        status=(
            Application.Status.PENDING
            if save_as_draft
            else Application.Status.SUBMITTED
        ),
    )


    # -----------------------------
    # Create Company Details
    # -----------------------------
    CompanyDetails.objects.create(
        application=application,
        company_type=company_type,
        principal_business_activity=principal_business_activity,
        company_email=company_email,
        company_phone=company_phone,
        company_description=business_description,
    )


    # -----------------------------
    # Create Directors
    # -----------------------------
    for i in range(director_count):

        CompanyDirector.objects.create(
            application=application,
            first_name=director_first_names[i].strip(),
            last_name=director_last_names[i].strip(),
            email=director_emails[i].strip(),
            phone=director_phones[i].strip(),
            address=director_addresses[i].strip(),
            date_of_birth=director_dates_of_birth[i],
            nationality=director_nationalities[i].strip(),
        )


    # -----------------------------
    # Create Shareholders
    # -----------------------------
    for i in range(shareholder_count):

        CompanyShareholder.objects.create(
            application=application,
            full_name=shareholder_names[i].strip(),
            email=shareholder_emails[i].strip(),
            phone=shareholder_phones[i].strip(),
            number_of_shares=shareholder_shares[i],
            shareholding_percentage=shareholder_percentages[i],
        )


    # -----------------------------
    # Save reservation relationship
    # -----------------------------
    confirmed_reservation.save(
        update_fields=["updated_at"]
    )


    # -----------------------------
    # Draft
    # -----------------------------
    if save_as_draft:

        messages.success(
            request,
            "Company application saved as draft."
        )

        return redirect("dashboard:home")


    # -----------------------------
    # Create application payment
    # -----------------------------
    Payment.objects.create(
        user=request.user,
        application=application,
        payment_type=Payment.PaymentType.APPLICATION,
        amount=system_fee.application_fee,
    )


    return redirect(
        "applications:application_payment",
        reference_id=application.reference_id
    )




@login_required
def my_applications_api(request):
    qs = Application.objects.filter(user=request.user).order_by("-created_at")
    data = [
        {
            "reference_id": a.reference_id,
            "business_name": a.proposed_name_1,
            "registration_type": a.registration_type,
            "status": a.status,
            "status_label": a.get_status_display(),
            "agent_note": a.agent_note,
            "previous_notes": a.previous_notes,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        }
        for a in qs
    ]
    return JsonResponse({"applications": data})


# Function to Modify Submitted Application
@login_required
@require_http_methods(["GET", "POST"])
def modify_application(request, reference_id):

    app = get_object_or_404(
        Application,
        reference_id=reference_id,
        user=request.user
    )

    # ------------------------------------------------------------
    # ONLY QUERIED APPLICATIONS CAN BE MODIFIED
    # ------------------------------------------------------------

    if app.status != Application.Status.QUERIED:
        messages.error(
            request,
            "You cannot modify this application."
        )
        return redirect("dashboard:home")

    # ============================================================
    # COMPANY APPLICATION
    # ============================================================

    if app.registration_type == Application.RegistrationType.COMPANY:

        company_details = getattr(
            app,
            "company_details",
            None
        )

        # --------------------------------------------------------
        # GET REQUEST
        # --------------------------------------------------------

        if request.method == "GET":

            return render(
                request,
                "applications/modify-application.html",
                {
                    "app": app,
                    "reserved_name": (
                        app.name_reservation.proposed_name
                        if app.name_reservation
                        else app.proposed_name_1
                    ),
                    "company_details": company_details,
                    "directors": app.company_directors.all(),
                    "shareholders": app.company_shareholders.all(),
                }
            )

        # --------------------------------------------------------
        # KEEP PROPOSED NAME FROM OFFICIAL RESERVATION
        # --------------------------------------------------------

        if app.name_reservation:

            app.proposed_name_1 = normalize_business_name(
                app.name_reservation.proposed_name
            )

        else:

            app.proposed_name_1 = normalize_business_name(
                app.proposed_name_1
            )

        # --------------------------------------------------------
        # COMPANY DETAILS
        # --------------------------------------------------------

        company_type = (
            request.POST.get("company_type") or ""
        ).strip()

        principal_business_activity = (
            request.POST.get("principal_business_activity") or ""
        ).strip()

        state = (
            request.POST.get("state") or ""
        ).strip().upper()

        lga = (
            request.POST.get("lga") or ""
        ).strip().upper()

        business_address = (
            request.POST.get("business_address") or ""
        ).strip().upper()

        company_email = (
            request.POST.get("company_email") or ""
        ).strip()

        company_phone = (
            request.POST.get("company_phone") or ""
        ).strip()

        business_description = (
            request.POST.get("business_description") or ""
        ).strip()

        # --------------------------------------------------------
        # DIRECTORS
        # --------------------------------------------------------

        director_first_names = request.POST.getlist(
            "director_first_name[]"
        )

        director_last_names = request.POST.getlist(
            "director_last_name[]"
        )

        director_emails = request.POST.getlist(
            "director_email[]"
        )

        director_phones = request.POST.getlist(
            "director_phone[]"
        )

        director_addresses = request.POST.getlist(
            "director_address[]"
        )

        director_dates_of_birth = request.POST.getlist(
            "director_date_of_birth[]"
        )

        director_nationalities = request.POST.getlist(
            "director_nationality[]"
        )

        # --------------------------------------------------------
        # SHAREHOLDERS
        # --------------------------------------------------------

        shareholder_names = request.POST.getlist(
            "shareholder_full_name[]"
        )

        shareholder_emails = request.POST.getlist(
            "shareholder_email[]"
        )

        shareholder_phones = request.POST.getlist(
            "shareholder_phone[]"
        )

        shareholder_shares = request.POST.getlist(
            "shareholder_number_of_shares[]"
        )

        shareholder_percentages = request.POST.getlist(
            "shareholder_shareholding_percentage[]"
        )

        # --------------------------------------------------------
        # VALIDATION
        # --------------------------------------------------------

        errors = []

        if not company_details:
            errors.append(
                "Company details could not be found."
            )

        if not app.proposed_name_1:
            errors.append(
                "Proposed Company Name is required."
            )

        if not company_type:
            errors.append(
                "Company Type is required."
            )

        if not principal_business_activity:
            errors.append(
                "Principal Business Activity is required."
            )

        if not state:
            errors.append(
                "State is required."
            )

        if not lga:
            errors.append(
                "LGA is required."
            )

        if not business_address:
            errors.append(
                "Registered Office Address is required."
            )

        if not company_email:
            errors.append(
                "Company Email is required."
            )

        if not company_phone:
            errors.append(
                "Company Phone is required."
            )

        # --------------------------------------------------------
        # VALIDATE DIRECTORS
        # --------------------------------------------------------

        director_count = len(director_first_names)

        if director_count == 0:

            errors.append(
                "At least one Director is required."
            )

        elif not (
            len(director_last_names) == director_count
            and len(director_emails) == director_count
            and len(director_phones) == director_count
            and len(director_addresses) == director_count
            and len(director_dates_of_birth) == director_count
            and len(director_nationalities) == director_count
        ):

            errors.append(
                "Please complete all Director information."
            )

        # --------------------------------------------------------
        # VALIDATE SHAREHOLDERS
        # --------------------------------------------------------

        shareholder_count = len(shareholder_names)

        if shareholder_count == 0:

            errors.append(
                "At least one Shareholder is required."
            )

        elif not (
            len(shareholder_emails) == shareholder_count
            and len(shareholder_phones) == shareholder_count
            and len(shareholder_shares) == shareholder_count
            and len(shareholder_percentages) == shareholder_count
        ):

            errors.append(
                "Please complete all Shareholder information."
            )

        # --------------------------------------------------------
        # VALIDATE DIRECTOR DATES
        # --------------------------------------------------------

        from datetime import date

        director_birth_dates = []

        if director_count > 0 and (
            len(director_dates_of_birth) == director_count
        ):

            for i in range(director_count):

                try:

                    birth_date = date.fromisoformat(
                        director_dates_of_birth[i]
                    )

                    director_birth_dates.append(
                        birth_date
                    )

                except (ValueError, TypeError):

                    errors.append(
                        f"Invalid date of birth for Director {i + 1}."
                    )

        # --------------------------------------------------------
        # VALIDATE SHARE VALUES
        # --------------------------------------------------------

        validated_share_numbers = []
        validated_share_percentages = []

        if shareholder_count > 0 and (
            len(shareholder_shares) == shareholder_count
            and len(shareholder_percentages) == shareholder_count
        ):

            for i in range(shareholder_count):

                try:

                    number_of_shares = int(
                        shareholder_shares[i]
                    )

                    if number_of_shares <= 0:
                        raise ValueError

                    validated_share_numbers.append(
                        number_of_shares
                    )

                except (ValueError, TypeError):

                    errors.append(
                        f"Invalid number of shares for Shareholder {i + 1}."
                    )

                try:

                    percentage = float(
                        shareholder_percentages[i]
                    )

                    if percentage < 0 or percentage > 100:
                        raise ValueError

                    validated_share_percentages.append(
                        percentage
                    )

                except (ValueError, TypeError):

                    errors.append(
                        f"Invalid shareholding percentage for Shareholder {i + 1}."
                    )

        # --------------------------------------------------------
        # IF VALIDATION FAILS
        # --------------------------------------------------------

        if errors:

            for error in errors:
                messages.error(
                    request,
                    error
                )

            return render(
                request,
                "applications/modify-application.html",
                {
                    "app": app,
                    "reserved_name": (
                        app.name_reservation.proposed_name
                        if app.name_reservation
                        else app.proposed_name_1
                    ),
                    "company_details": company_details,
                    "directors": app.company_directors.all(),
                    "shareholders": app.company_shareholders.all(),
                }
            )

        # ========================================================
        # UPDATE APPLICATION
        # ========================================================

        app.nature_of_business = (
            principal_business_activity
        )

        app.business_type = company_type

        app.state = state

        app.lga = lga

        app.business_address = business_address

        # Company applications do not use proprietor names
        app.owner_first_name = ""
        app.owner_last_name = ""

        app.owner_email = company_email
        app.owner_phone = company_phone

        app.business_description = (
            business_description
        )

        # --------------------------------------------------------
        # FILE UPDATES
        # --------------------------------------------------------

        if request.FILES.get("passport"):

            app.passport = request.FILES.get(
                "passport"
            )

        if request.FILES.get("signature"):

            app.signature = request.FILES.get(
                "signature"
            )

        if request.FILES.get("nin"):

            app.nin = request.FILES.get(
                "nin"
            )

        # --------------------------------------------------------
        # SAVE APPLICATION
        # --------------------------------------------------------

        app.save()

        # ========================================================
        # UPDATE COMPANY DETAILS
        # ========================================================

        company_details.company_type = company_type

        company_details.principal_business_activity = (
            principal_business_activity
        )

        company_details.company_email = company_email

        company_details.company_phone = company_phone

        company_details.company_description = (
            business_description
        )

        company_details.save()

        # ========================================================
        # UPDATE DIRECTORS
        # ========================================================

        app.company_directors.all().delete()

        for i in range(director_count):

            CompanyDirector.objects.create(
                application=app,
                first_name=director_first_names[i].strip(),
                last_name=director_last_names[i].strip(),
                email=director_emails[i].strip(),
                phone=director_phones[i].strip(),
                address=director_addresses[i].strip(),
                date_of_birth=director_birth_dates[i],
                nationality=director_nationalities[i].strip(),
            )

        # ========================================================
        # UPDATE SHAREHOLDERS
        # ========================================================

        app.company_shareholders.all().delete()

        for i in range(shareholder_count):

            CompanyShareholder.objects.create(
                application=app,
                full_name=shareholder_names[i].strip(),
                email=shareholder_emails[i].strip(),
                phone=shareholder_phones[i].strip(),
                number_of_shares=validated_share_numbers[i],
                shareholding_percentage=(
                    validated_share_percentages[i]
                ),
            )

        # ========================================================
        # CLEAR QUERY AND RESUBMIT
        # ========================================================

        app.clear_query_note()

        messages.success(
            request,
            "Company application corrected and resubmitted successfully."
        )

        return redirect(
            "dashboard:home"
        )

    # ============================================================
    # EXISTING BUSINESS APPLICATION
    # ============================================================

    # ------------------------------------------------------------
    # GET REQUEST
    # ------------------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "applications/modify-application.html",
            {
                "app": app,
                "reserved_name": (
                    app.name_reservation.proposed_name
                    if app.name_reservation
                    else app.proposed_name_1
                ),
            }
        )

    # ------------------------------------------------------------
    # KEEP PROPOSED NAME FROM OFFICIAL RESERVATION
    # ------------------------------------------------------------

    if app.name_reservation:

        app.proposed_name_1 = normalize_business_name(
            app.name_reservation.proposed_name
        )

    else:

        app.proposed_name_1 = normalize_business_name(
            app.proposed_name_1
        )

    # ------------------------------------------------------------
    # UPDATE BUSINESS FIELDS
    # ------------------------------------------------------------

    app.proposed_name_2 = normalize_business_name(
        request.POST.get(
            "proposed_name_2",
            ""
        )
    )

    app.nature_of_business = (
        request.POST.get(
            "nature_of_business"
        ) or ""
    ).strip()

    app.business_type = (
        request.POST.get(
            "business_type"
        ) or ""
    ).strip()

    app.state = (
        request.POST.get(
            "state"
        ) or ""
    ).strip().upper()

    app.lga = (
        request.POST.get(
            "lga"
        ) or ""
    ).strip().upper()

    app.business_address = (
        request.POST.get(
            "business_address"
        ) or ""
    ).strip().upper()

    app.owner_first_name = (
        request.POST.get(
            "owner_first_name"
        ) or ""
    ).strip()

    app.owner_last_name = (
        request.POST.get(
            "owner_last_name"
        ) or ""
    ).strip()

    app.owner_email = (
        request.POST.get(
            "owner_email"
        ) or ""
    ).strip()

    app.owner_phone = (
        request.POST.get(
            "owner_phone"
        ) or ""
    ).strip()

    app.business_description = (
        request.POST.get(
            "business_description"
        ) or ""
    ).strip()

    # ------------------------------------------------------------
    # FILE UPDATES
    # ------------------------------------------------------------

    if request.FILES.get("passport"):

        app.passport = request.FILES.get(
            "passport"
        )

    if request.FILES.get("signature"):

        app.signature = request.FILES.get(
            "signature"
        )

    if request.FILES.get("nin"):

        app.nin = request.FILES.get(
            "nin"
        )

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    errors = []

    required_fields = [
        (
            "proposed_name_1",
            "Proposed Business Name"
        ),
        (
            "nature_of_business",
            "Nature of Business"
        ),
        (
            "business_type",
            "Business Type"
        ),
        (
            "state",
            "State"
        ),
        (
            "lga",
            "LGA"
        ),
        (
            "business_address",
            "Business Address"
        ),
        (
            "owner_first_name",
            "Owner First Name"
        ),
        (
            "owner_last_name",
            "Owner Last Name"
        ),
        (
            "owner_email",
            "Owner Email"
        ),
        (
            "owner_phone",
            "Owner Phone"
        ),
    ]

    for field, label in required_fields:

        if not getattr(app, field):

            errors.append(
                f"{label} is required."
            )

    # ------------------------------------------------------------
    # VALIDATION ERRORS
    # ------------------------------------------------------------

    if errors:

        for error in errors:

            messages.error(
                request,
                error
            )

        return render(
            request,
            "applications/modify-application.html",
            {
                "app": app,
                "reserved_name": (
                    app.name_reservation.proposed_name
                    if app.name_reservation
                    else app.proposed_name_1
                ),
            }
        )

    # ------------------------------------------------------------
    # SAVE BUSINESS APPLICATION
    # ------------------------------------------------------------

    app.save()

    # ------------------------------------------------------------
    # CLEAR QUERY AND RESUBMIT
    # ------------------------------------------------------------

    app.clear_query_note()

    messages.success(
        request,
        "Application corrected and resubmitted successfully."
    )

    return redirect(
        "dashboard:home"
    )



# Function to download certificate for the user when authenticated
@login_required
def download_certificate(request, reference_id):

    application = get_object_or_404(
        Application,
        reference_id=reference_id,
        user=request.user
    )

    payment = Payment.objects.filter(
        application=application,
        payment_type=Payment.PaymentType.APPLICATION
    ).order_by("-created_at").first()

    if (
        not payment
        or payment.status != Payment.Status.CONFIRMED
    ):
        return HttpResponse(
            "Certificate not available because application payment has not been confirmed.",
            status=403
        )

    if application.status != Application.Status.APPROVED:
        return HttpResponse(
            "Certificate not available",
            status=403
        )

    if not application.certificate:
        return HttpResponse(
            "Certificate file not found.",
            status=404
        )

    return FileResponse(
        application.certificate.open("rb"),
        as_attachment=True,
        filename=f"certificate_{application.registration_number}.pdf",
    )

# Function to view certificate when authenticated
@login_required
def view_certificate(request, reference_id):

    application = get_object_or_404(
        Application,
        reference_id=reference_id,
        user=request.user
    )

    payment = Payment.objects.filter(
        application=application,
        payment_type=Payment.PaymentType.APPLICATION
    ).order_by("-created_at").first()

    if (
        not payment
        or payment.status != Payment.Status.CONFIRMED
    ):
        return HttpResponse(
            "Certificate not available because "
            "application payment has not been confirmed.",
            status=403  
        )

    if application.status != Application.Status.APPROVED:
        return HttpResponse(
            "Certificate not available", 
            status=403
        )

    if not application.certificate:
        return HttpResponse(
            "Certificate file not found.", 
            status=404
        )

    return render(
        request,
        "certificate/certificate.html",
        {
            "application": application
        }
    )

#Function to Verify Certificate for the qrcode
@csrf_exempt
def verify_certificate(request,token):
    token = request.GET.get("token")
    
    valid = False
    application = None
    qr_code_url = None
    try:
        application = Application.objects.get(
            verification_token=token,
            status=Application.Status.APPROVED
        )
        # Recalculate signature
        data = f"{application.registration_number}{application.proposed_name_1}{application.owner_first_name}{application.owner_last_name}{application.approved_at}"
        recalculated_signature = hashlib.sha256(data.encode("utf-8")).hexdigest()

        # Check integrity
        if recalculated_signature == application.digital_signature:
            valid = True
        
        if application.qr_code:
            qr_code_url =application.qr_code.url
        else:
            valid = False
            
    except Application.DoesNotExist:
        application = None
        valid = False
        qr_code_url = None
        

    return render(request, "certificate/verify.html", {
        "application": application,
        "valid": valid,
        "qr_code_url":qr_code_url
    })

# Function to verify the certificate publicly using RC-NUMBER
def public_search(request):
    reg_number = request.GET.get("registration_number", "").strip()
    application = None
    valid = False
    qr_code_url = None

    if reg_number:
        try:
            application = Application.objects.get(
                registration_number=reg_number,
                status=Application.Status.APPROVED
            )

            # Recalculate signature for tamper-proof check
            data = f"{application.registration_number}{application.proposed_name_1}{application.owner_first_name}{application.owner_last_name}{application.approved_at}"
            recalculated_signature = hashlib.sha256(data.encode("utf-8")).hexdigest()
            valid = recalculated_signature == application.digital_signature

            if application.qr_code:
                qr_code_url = application.qr_code.url

        except Application.DoesNotExist:
            application = None
            valid = False
            qr_code_url = None

    return render(request, "frontend/index.html", {
        "application": application,
        "valid": valid,
        "qr_code_url": qr_code_url,
        "search_query": reg_number,
    })

#Function to display certificate for the public
def public_certificate(request, token):

    application = get_object_or_404(
        Application,
        verification_token=token,
        status=Application.Status.APPROVED
    )

    payment = Payment.objects.filter(
        application=application,
        payment_type=Payment.PaymentType.APPLICATION
    ).order_by("-created_at").first()

    if (
        not payment
        or payment.status != Payment.Status.CONFIRMED
    ):
        return render(
            request,
            "error.html",
            {
                "message":
                    "This certificate is not available because "
                    "the application payment has not been confirmed."
            }
        )

    return render(
        request,
        "certificate/certificate.html",
        {
            "application": application
        }
    )