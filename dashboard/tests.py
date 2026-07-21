from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardViewTests(TestCase):

    def setUp(self):
        # Normal user
        self.user = User.objects.create_user(
            username="john",
            password="password123"
        )

        # Staff user
        self.staff = User.objects.create_user(
            username="admin",
            password="password123",
            is_staff=True
        )

    # Testing Anonymous users should be redirected to login
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    # Testing Normal Users can access dashboard
    def test_normal_user_can_access_dashboard(self):

        self.client.login(
            username="john",
            password="password123"
        )

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/dashboard.html"
        )

    #Testing Staff User should be redirected to admin 
    def test_staff_user_redirected_to_admin(self):

        self.client.login(
            username="admin",
            password="password123"
        )

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")
    
    