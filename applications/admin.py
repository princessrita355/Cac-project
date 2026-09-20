
from django.utils.html import format_html
from django.contrib import admin, messages
from .models import (
    Application,
    NameReservation,
    Payment,
    SystemFee,
    CompanyDetails,
    CompanyDirector,
    CompanyShareholder,
)
from django.utils.safestring import mark_safe
from django import forms
from django.utils import timezone


# =========================================================
# COMPANY INLINE SECTIONS
# =========================================================

class CompanyDetailsInline(admin.StackedInline):
    model = CompanyDetails
    extra = 0
    max_num = 1
    can_delete = False

    readonly_fields = (
        "company_type",
        "principal_business_activity",
        "company_email",
        "company_phone",
        "company_description",
        "created_at",
        "updated_at",
    )

    fields = (
        "company_type",
        "principal_business_activity",
        "company_email",
        "company_phone",
        "company_description",
        "created_at",
        "updated_at",
    )


class CompanyDirectorInline(admin.TabularInline):
    model = CompanyDirector
    extra = 0
    can_delete = False

    readonly_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "date_of_birth",
        "nationality",
        "created_at",
    )

    fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "date_of_birth",
        "nationality",
        "created_at",
    )


class CompanyShareholderInline(admin.TabularInline):
    model = CompanyShareholder
    extra = 0
    can_delete = False

    readonly_fields = (
        "full_name",
        "email",
        "phone",
        "number_of_shares",
        "shareholding_percentage",
        "created_at",
    )

    fields = (
        "full_name",
        "email",
        "phone",
        "number_of_shares",
        "shareholding_percentage",
        "created_at",
    )


# =========================================================
# APPLICATION ADMIN FORM
# =========================================================

class ApplicationAdminForm(forms.ModelForm):

    class Meta:
        model = Application
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:

            self.fields["agent_note"].initial = ""

            self.fields["agent_note"].widget.attrs.update({
                "placeholder": "Type new query here...",
                "style": "resize: none;"
            })


# =========================================================
# APPLICATION ADMIN
# =========================================================

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):

    form = ApplicationAdminForm

    list_display = (
        "reference_id",
        "proposed_name_1",
        "registration_type_display",
        "user",
        "colored_status",
        "updated_at",
        "passport_preview",
        "signature_preview",
        "nin_preview",
        "account_type",
        "registration_number_display",
        "qr_code_preview",
    )

    list_filter = (
        "status",
        "registration_type",
        "created_at",
        "user__profile__account_type",
    )

    search_fields = (
        "reference_id",
        "proposed_name_1",
        "user__email",
        "user__username",
        "registration_number",
    )

    # =====================================================
    # COMPANY INLINES ONLY FOR COMPANY APPLICATIONS
    # =====================================================

    def get_inline_instances(self, request, obj=None):

        if (
            obj
            and obj.registration_type
            == Application.RegistrationType.COMPANY
        ):

            return [
                CompanyDetailsInline(self.model, self.admin_site),
                CompanyDirectorInline(self.model, self.admin_site),
                CompanyShareholderInline(self.model, self.admin_site),
            ]

        return []

    # =====================================================
    # READONLY FIELDS
    # =====================================================

    readonly_fields = (
        "reference_id",
        "created_at",
        "updated_at",
        "user",
        "registration_type",
        "proposed_name_1",
        "proposed_name_2",
        "nature_of_business",
        "business_type",
        "state",
        "lga",
        "business_address",
        "owner_first_name",
        "owner_last_name",
        "owner_email",
        "owner_phone",
        "business_description",
        "passport",
        "signature",
        "nin",
        "status",
        "highlighted_query_note",
        "previous_query_notes",
        "qr_code_preview",
        "registration_number_display",
    )

    # =====================================================
    # BUSINESS FIELDSET
    # =====================================================

    business_fieldsets = (
        (
            "Business",
            {
                "fields": (
                    "proposed_name_1",
                    "proposed_name_2",
                    "nature_of_business",
                    "business_type",
                    "business_description",
                )
            },
        ),

        (
            "Address",
            {
                "fields": (
                    "state",
                    "lga",
                    "business_address",
                )
            },
        ),

        (
            "Owner",
            {
                "fields": (
                    "owner_first_name",
                    "owner_last_name",
                    "owner_email",
                    "owner_phone",
                )
            },
        ),
    )

    # =====================================================
    # COMPANY FIELDSET
    # =====================================================

    company_fieldsets = (
        (
            "Company",
            {
                "fields": (
                    "proposed_name_1",
                    "state",
                    "lga",
                    "business_address",
                )
            },
        ),
    )

    # =====================================================
    # DYNAMIC FIELDSETS
    # =====================================================

    def get_fieldsets(self, request, obj=None):

        common_fieldsets = (
            (
                "User Query",
                {
                    "fields": (
                        "highlighted_query_note",
                        "previous_query_notes",
                        "agent_note",
                    )
                },
            ),

            (
                "Reference & Status",
                {
                    "fields": (
                        "status",
                        "registration_type",
                        "qr_code_preview",
                        "registration_number_display",
                    )
                },
            ),
        )

        upload_fieldset = (
            (
                "Uploads",
                {
                    "fields": (
                        "passport",
                        "signature",
                        "nin",
                    )
                },
            ),

            (
                "Meta",
                {
                    "fields": (
                        "user",
                    )
                },
            ),
        )

        # -------------------------------------------------
        # NEW APPLICATION
        # -------------------------------------------------

        if obj is None:
            return common_fieldsets + (
                (
                    "Registration Information",
                    {
                        "fields": (
                            "registration_type",
                            "proposed_name_1",
                        )
                    },
                ),
            ) + upload_fieldset

        # -------------------------------------------------
        # COMPANY APPLICATION
        # -------------------------------------------------

        if (
            obj.registration_type
            == Application.RegistrationType.COMPANY
        ):

            return common_fieldsets + self.company_fieldsets + upload_fieldset

        # -------------------------------------------------
        # BUSINESS APPLICATION
        # -------------------------------------------------

        return common_fieldsets + self.business_fieldsets + upload_fieldset

    # =====================================================
    # QUERY DISPLAY
    # =====================================================

    def highlighted_query_note(self, obj):

        if obj.agent_note:

            return format_html(
                "<div>{}</div>",
                obj.agent_note
            )

        return "-"

    highlighted_query_note.short_description = "Active Query"

    def previous_query_notes(self, obj):

        if obj.previous_notes:

            html = "".join(
                f'<div style="margin-bottom:5px;">{note}</div>'
                for note in reversed(obj.previous_notes)
            )

            return mark_safe(html)

        return "-"

    previous_query_notes.short_description = "Previous Queries"

    # =====================================================
    # REGISTRATION NUMBER
    # =====================================================

    def registration_number_display(self, obj):

        return obj.registration_number or "-"

    registration_number_display.short_description = "RC Number"

    # =====================================================
    # REGISTRATION TYPE
    # =====================================================

    def registration_type_display(self, obj):

        if (
            obj.registration_type
            == Application.RegistrationType.COMPANY
        ):
            return "Company"

        return "Business Name"

    registration_type_display.short_description = "Registration Type"

    # =====================================================
    # SAVE MODEL
    # =====================================================



    def save_model(self, request, obj, form, change):

        if change:

            old_obj = Application.objects.get(
                pk=obj.pk
            )

            # =================================================
            # CHECK APPLICATION PAYMENT
            # =================================================

            application_payment = Payment.objects.filter(
                application=obj,
                payment_type=Payment.PaymentType.APPLICATION
            ).order_by("-created_at").first()

            payment_confirmed = (
                application_payment
                and application_payment.status
                == Payment.Status.CONFIRMED
            )

            # =================================================
            # PREVENT REVIEW/APPROVAL BEFORE PAYMENT CONFIRMATION
            # =================================================

            if (
                obj.status in (
                    Application.Status.QUERIED,
                    Application.Status.APPROVED,
                )
                and not payment_confirmed
            ):

                obj.status = old_obj.status

                self.message_user(
                    request,
                    "This application cannot be reviewed or approved "
                    "until the application payment has been confirmed.",
                    messages.ERROR,
                )

            # =================================================
            # APPROVE APPLICATION
            # =================================================

            elif (
                obj.status == Application.Status.APPROVED
                and old_obj.status
                != Application.Status.APPROVED
            ):

                # ---------------------------------------------
                # FINAL PAYMENT SAFETY CHECK
                # ---------------------------------------------

                if not payment_confirmed:

                    obj.status = old_obj.status

                    self.message_user(
                        request,
                        "Application cannot be approved because "
                        "the payment has not been confirmed.",
                        messages.ERROR,
                    )

                else:

                    if not obj.registration_number:

                        obj.registration_number = (
                            obj.generate_registration_number()
                        )

                    if not obj.verification_token:

                        obj.verification_token = (
                            obj.generate_verification_token()
                        )

                    obj.generate_qr_code()

                    obj.approved_at = timezone.now()

                    obj.approved_by = request.user

                    obj.generate_signature()

                    obj.generate_and_save_certificate()

            # =================================================
            # QUERY NOTES
            # =================================================

            new_note = (
                form.cleaned_data
                .get("agent_note", "")
                .strip()
            )

            if (
                new_note
                and payment_confirmed
            ):

                if obj.agent_note:

                    obj.previous_notes.append(
                        obj.agent_note
                    )

                obj.agent_note = new_note

                obj.status = (
                    Application.Status.QUERIED
                )

        super().save_model(
            request,
            obj,
            form,
            change
        )

    # =====================================================
    # ACCOUNT TYPE
    # =====================================================

    def account_type(self, obj):

        if hasattr(obj.user, "profile"):
            return obj.user.profile.account_type

        return "N/A"

    account_type.short_description = "Account Type"

    # =====================================================
    # PERMISSIONS
    # =====================================================

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):

        method_fields = (
            "highlighted_query_note",
            "previous_query_notes",
            "registration_number_display",
            "qr_code_preview",
        )

        if request.user.is_superuser:

            return method_fields

        readonly = [
            field
            for field in self.readonly_fields
            if field not in (
                "agent_note",
                "status",
            )
        ]

        return list(readonly) + list(method_fields)

    # =====================================================
    # ACTIONS
    # =====================================================

    actions = [
        "mark_approved",
        "mark_queried",
    ]

    # -----------------------------------------------------
    # APPROVE APPLICATION
    # -----------------------------------------------------

    @admin.action(
    description="Mark selected applications as Approved"
)
    def mark_approved(self, request, queryset):

        approved_count = 0
        skipped_count = 0

        for obj in queryset:

            payment = Payment.objects.filter(
                application=obj,
                payment_type=Payment.PaymentType.APPLICATION
            ).order_by("-created_at").first()

            payment_confirmed = (
                payment
                and payment.status
                == Payment.Status.CONFIRMED
            )

            if not payment_confirmed:

                skipped_count += 1

                continue

            if obj.status == Application.Status.APPROVED:

                skipped_count += 1

                continue

            obj.approve(
                staff_user=request.user
            )

            approved_count += 1

        if approved_count:

            self.message_user(
                request,
                f"{approved_count} application(s) approved successfully.",
                messages.SUCCESS,
            )

        if skipped_count:

            self.message_user(
                request,
                f"{skipped_count} application(s) were skipped because "
                f"their application payment has not been confirmed "
                f"or they are already approved.",
                messages.WARNING,
            )

    # -----------------------------------------------------
    # MARK AS QUERIED
    # -----------------------------------------------------

    @admin.action(
    description="Mark selected applications as Queried"
)
    def mark_queried(self, request, queryset):

        queried_count = 0
        skipped_count = 0

        for obj in queryset:

            payment = Payment.objects.filter(
                application=obj,
                payment_type=Payment.PaymentType.APPLICATION
            ).order_by("-created_at").first()

            payment_confirmed = (
                payment
                and payment.status
                == Payment.Status.CONFIRMED
            )

            if not payment_confirmed:

                skipped_count += 1

                continue

            if obj.status == Application.Status.APPROVED:

                skipped_count += 1

                continue

            if obj.agent_note:

                obj.previous_notes.append(
                    obj.agent_note
                )

            obj.agent_note = ""

            obj.status = (
                Application.Status.QUERIED
            )

            obj.save()

            queried_count += 1

        if queried_count:

            self.message_user(
                request,
                f"{queried_count} application(s) marked as queried.",
                messages.SUCCESS,
            )

        if skipped_count:

            self.message_user(
                request,
                f"{skipped_count} application(s) were skipped because "
                f"their application payment has not been confirmed "
                f"or they are already approved.",
                messages.WARNING,
            )

    # =====================================================
    # FILE PREVIEWS
    # =====================================================

    def passport_preview(self, obj):

        if obj.passport:

            return format_html(
                '<img src="{}" width="50"/>',
                obj.passport.url
            )

        return "-"

    passport_preview.short_description = "Passport"

    def signature_preview(self, obj):

        if obj.signature:

            return format_html(
                '<img src="{}" width="50"/>',
                obj.signature.url
            )

        return "-"

    signature_preview.short_description = "Signature"

    def nin_preview(self, obj):

        if obj.nin:

            if obj.nin.url.lower().endswith(".pdf"):

                return format_html(
                    '<a href="{}" target="_blank">PDF</a>',
                    obj.nin.url
                )

            return format_html(
                '<img src="{}" width="50"/>',
                obj.nin.url
            )

        return "-"

    nin_preview.short_description = "NIN"

    def qr_code_preview(self, obj):

        if obj.qr_code:

            return format_html(
                '<img src="{}" width="30"/>',
                obj.qr_code.url
            )

        return "-"

    qr_code_preview.short_description = "QR Code"

    # =====================================================
    # COLORED STATUS
    # =====================================================

    def colored_status(self, obj):

        color = {
            "submitted": "gray",
            "pending": "orange",
            "queried": "red",
            "approved": "green",
        }.get(
            obj.status,
            "black"
        )

        return format_html(
            '<span style="color:{};">{}</span>',
            color,
            obj.get_status_display()
        )

    colored_status.short_description = "Status"


# =========================================================
# SYSTEM FEE ADMIN
# =========================================================

@admin.register(SystemFee)
class SystemFeeAdmin(admin.ModelAdmin):

    list_display = (
        "name_reservation_fee",
        "application_fee",
        "updated_at",
    )

    fields = (
        "name_reservation_fee",
        "application_fee",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )


# =========================================================
# NAME RESERVATION ADMIN
# =========================================================

@admin.register(NameReservation)
class NameReservationAdmin(admin.ModelAdmin):

    list_display = (
        "reference_id",
        "proposed_name",
        "user",
        "registration_type",
        "reservation_fee",
        "status",
        "payment_reference",
        "created_at",
        "confirmed_at",
    )

    list_filter = (
        "status",
        "registration_type",
        "created_at",
        "confirmed_at",
    )

    search_fields = (
        "reference_id",
        "proposed_name",
        "user__email",
        "user__username",
        "payment_reference",
    )

    readonly_fields = (
        "reference_id",
        "user",
        "proposed_name",
        "registration_type",
        "reservation_fee",
        "payment_reference",
        "payment_submitted_at",
        "confirmed_at",
        "confirmed_by",
        "created_at",
        "updated_at",
    )


# =========================================================
# PAYMENT ADMIN
# =========================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "payment_reference",
        "user",
        "payment_type",
        "amount",
        "status",
        "created_at",
        "submitted_at",
        "confirmed_at",
        "confirmed_by",
    )

    list_filter = (
        "payment_type",
        "status",
        "created_at",
        "confirmed_at",
    )

    search_fields = (
        "payment_reference",
        "user__email",
        "user__username",
        "reservation__reference_id",
        "reservation__proposed_name",
    )

    readonly_fields = (
        "user",
        "payment_type",
        "reservation",
        "application",
        "amount",
        "payment_reference",
        "created_at",
        "submitted_at",
        "confirmed_at",
        "confirmed_by",
    )

    actions = [
        "confirm_selected_payments",
    ]

    # =====================================================
    # SAVE PAYMENT
    # =====================================================

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        old_status = None

        if change:

            old_obj = Payment.objects.get(
                pk=obj.pk
            )

            old_status = old_obj.status

        super().save_model(
            request,
            obj,
            form,
            change
        )

        # =================================================
        # APPLICATION PAYMENT
        # =================================================

        if (
            obj.payment_type
            == Payment.PaymentType.APPLICATION
        ):

            application = obj.application

            if not application:
                return

            # ---------------------------------------------
            # PAYMENT CONFIRMED
            # ---------------------------------------------

            if obj.status == Payment.Status.CONFIRMED:

                if (
                    old_status
                    != Payment.Status.CONFIRMED
                    or not obj.confirmed_at
                    or not obj.confirmed_by
                ):

                    obj.confirmed_at = timezone.now()
                    obj.confirmed_by = request.user

                    obj.save(
                        update_fields=[
                            "confirmed_at",
                            "confirmed_by",
                        ]
                    )

                if (
                    application.status
                    != Application.Status.APPROVED
                ):

                    application.status = (
                        Application.Status.PENDING
                    )

                    application.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

            # ---------------------------------------------
            # PAYMENT SUBMITTED
            # ---------------------------------------------

            elif obj.status == Payment.Status.SUBMITTED:

                obj.confirmed_at = None
                obj.confirmed_by = None

                obj.save(
                    update_fields=[
                        "confirmed_at",
                        "confirmed_by",
                    ]
                )

            # ---------------------------------------------
            # PAYMENT FAILED
            # ---------------------------------------------

            elif obj.status == Payment.Status.FAILED:

                obj.confirmed_at = None
                obj.confirmed_by = None

                obj.save(
                    update_fields=[
                        "confirmed_at",
                        "confirmed_by",
                    ]
                )

            return

        # =================================================
        # NAME RESERVATION PAYMENT
        # =================================================

        if (
            obj.payment_type
            != Payment.PaymentType.NAME_RESERVATION
        ):
            return

        reservation = obj.reservation

        if not reservation:
            return

        # -------------------------------------------------
        # PAYMENT CONFIRMED
        # -------------------------------------------------

        if obj.status == Payment.Status.CONFIRMED:

            if (
                old_status
                != Payment.Status.CONFIRMED
                or not obj.confirmed_at
                or not obj.confirmed_by
            ):

                obj.confirmed_at = timezone.now()
                obj.confirmed_by = request.user

                obj.save(
                    update_fields=[
                        "confirmed_at",
                        "confirmed_by",
                    ]
                )

            reservation.status = (
                NameReservation.Status.RESERVED
            )

            reservation.confirmed_at = (
                obj.confirmed_at
            )

            reservation.confirmed_by = request.user

            reservation.save(
                update_fields=[
                    "status",
                    "confirmed_at",
                    "confirmed_by",
                    "updated_at",
                ]
            )

        # -------------------------------------------------
        # PAYMENT SUBMITTED
        # -------------------------------------------------

        elif obj.status == Payment.Status.SUBMITTED:

            reservation.status = (
                NameReservation.Status.PAYMENT_SUBMITTED
            )

            reservation.confirmed_at = None
            reservation.confirmed_by = None

            reservation.save(
                update_fields=[
                    "status",
                    "confirmed_at",
                    "confirmed_by",
                    "updated_at",
                ]
            )

            obj.confirmed_at = None
            obj.confirmed_by = None

            obj.save(
                update_fields=[
                    "confirmed_at",
                    "confirmed_by",
                ]
            )

        # -------------------------------------------------
        # PAYMENT FAILED
        # -------------------------------------------------

        elif obj.status == Payment.Status.FAILED:

            reservation.status = (
                NameReservation.Status.AWAITING_PAYMENT
            )

            reservation.confirmed_at = None
            reservation.confirmed_by = None

            reservation.save(
                update_fields=[
                    "status",
                    "confirmed_at",
                    "confirmed_by",
                    "updated_at",
                ]
            )

            obj.confirmed_at = None
            obj.confirmed_by = None

            obj.save(
                update_fields=[
                    "confirmed_at",
                    "confirmed_by",
                ]
            )

    # =====================================================
    # CONFIRM SELECTED PAYMENTS
    # =====================================================

    @admin.action(
        description="Confirm selected payment(s)"
    )
    def confirm_selected_payments(
        self,
        request,
        queryset
    ):

        confirmed_count = 0
        skipped_count = 0

        for payment in queryset:

            if (
                payment.status
                != Payment.Status.SUBMITTED
            ):

                skipped_count += 1
                continue

            now = timezone.now()

            # =================================================
            # NAME RESERVATION PAYMENT
            # =================================================

            if (
                payment.payment_type
                == Payment.PaymentType.NAME_RESERVATION
            ):

                reservation = payment.reservation

                if not reservation:

                    skipped_count += 1
                    continue

                if (
                    reservation.status
                    != NameReservation.Status.PAYMENT_SUBMITTED
                ):

                    skipped_count += 1
                    continue

                payment.status = (
                    Payment.Status.CONFIRMED
                )

                payment.confirmed_at = now
                payment.confirmed_by = request.user

                payment.save(
                    update_fields=[
                        "status",
                        "confirmed_at",
                        "confirmed_by",
                    ]
                )

                reservation.status = (
                    NameReservation.Status.RESERVED
                )

                reservation.confirmed_at = now
                reservation.confirmed_by = request.user

                reservation.save(
                    update_fields=[
                        "status",
                        "confirmed_at",
                        "confirmed_by",
                        "updated_at",
                    ]
                )

                confirmed_count += 1

            # =================================================
            # APPLICATION PAYMENT
            # =================================================

            elif (
                payment.payment_type
                == Payment.PaymentType.APPLICATION
            ):

                application = payment.application

                if not application:

                    skipped_count += 1
                    continue

                payment.status = (
                    Payment.Status.CONFIRMED
                )

                payment.confirmed_at = now
                payment.confirmed_by = request.user

                payment.save(
                    update_fields=[
                        "status",
                        "confirmed_at",
                        "confirmed_by",
                    ]
                )

                application.status = (
                    Application.Status.PENDING
                )

                application.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                confirmed_count += 1

            else:

                skipped_count += 1

        # =================================================
        # SUCCESS MESSAGE
        # =================================================

        if confirmed_count:

            self.message_user(
                request,
                f"{confirmed_count} payment(s) confirmed successfully.",
                messages.SUCCESS,
            )

        # =================================================
        # SKIPPED MESSAGE
        # =================================================

        if skipped_count:

            self.message_user(
                request,
                f"{skipped_count} payment(s) were skipped because "
                f"they were not valid submitted payments.",
                messages.WARNING,
            )

