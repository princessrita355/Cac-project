from django.contrib.auth.models import User
from django.test import TestCase
from .models import Profile
from django.urls import reverse

# Testing The accounts Module that handles authentication logic
class ProfileModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="password123"
        )

        self.profile = Profile.objects.create(
            user=self.user,
            phone_number="08012345678",
            account_type="public"
        )

    def test_profile_created(self):
        """
        Profile should be created successfully.
        """
        self.assertEqual(Profile.objects.count(), 1)

    def test_profile_string_representation(self):
        """
        __str__ should return email and account type.
        """
        self.assertEqual(
            str(self.profile),
            "john@example.com (public)"
        )

        # Testing Signup
class signUpViewTest(TestCase):
    # Testing the Signup LOgic
    def test_signup_page_loads(self):

        response = self.client.get(
            reverse("accounts:signup")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/signup.html"
        )

    # Testing for Successful SIgnup
    def test_successful_signup(self):

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone_number": "08012345678",
                "account_type": "public",
                "password1": "My$ecureP@ss9876",
                "password2": "My$ecureP@ss9876",
                "terms": "on",
            },
           
        )
       

        self.assertRedirects(
            response,
            reverse("accounts:login")
        )

        self.assertEqual(User.objects.count(), 1)

        self.assertTrue(
            User.objects.filter(
                email="john@example.com"
            ).exists()
        )

        self.assertTrue(Profile.objects.filter(user__email="john@example.com").exists() )
        
        
    
    #Testing Password not matching
    def test_signup_password_mismatch(self):

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone_number": "08012345678",
                "account_type": "public",
                "password1": "abc123456",
                "password2": "xyz123456",
                "terms": "on",
            }
        )

        self.assertRedirects(
            response,
            reverse("accounts:signup")
        )

        self.assertEqual(User.objects.count(), 0)

# Testing the Login
class LoginViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="My$ecureP@ss9876"
        )

        self.staff = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="My$ecureP@ss9876",
            is_staff=True
        )


    # Login Page Testing
    def test_login_page_loads(self):

        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/login.html"
        )

    # Normal User login
    def test_normal_user_login(self):
        response = self.client.post(
                reverse("accounts:login"),
                {
                    "email": "john@example.com",
                    "password": "My$ecureP@ss9876",
                }
            )

        self.assertRedirects(
                response,
                reverse("dashboard:home")
            )

    # staff User Login
    def test_staff_login_redirects_to_admin(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "admin@example.com",
                "password": "My$ecureP@ss9876",
            }
        )

        self.assertRedirects(
            response,
            "/admin/"
        )

    # Test Wrong Password
    def test_invalid_password(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "john@example.com",
                "password": "WrongPassword123",
            }
        )

        self.assertRedirects(
            response,
            reverse("accounts:login")
        )

    # Test Unknown Email
    def test_unknown_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "unknown@example.com",
                "password": "My$ecureP@ss9876",
            }
        )

        self.assertRedirects(
            response,
            reverse("accounts:login")
        )


# Testing Logout
class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="My$ecureP@ss9876"
        )

    # Testing user redirect to login page after logout
    def test_logout_redirects_to_login(self):
        self.client.login(
                username="john@example.com",
                password="My$ecureP@ss9876"
            )

        response = self.client.get(
                reverse("accounts:logout")
            )

        self.assertRedirects(
                response,
                reverse("accounts:login")
            )
        
        #Testing Session is Cleared after Logout
    def test_logout_clears_session(self):
        self.client.login(
                username="john@example.com",
                password="My$ecureP@ss9876"
            )

        self.client.get(
                reverse("accounts:logout")
            )

        response = self.client.get(
                reverse("dashboard:home")
            )

            # User should now be redirected to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(
                reverse("accounts:login"),
                response.url
            )