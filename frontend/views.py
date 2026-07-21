from django.shortcuts import render


# Create your views here.
#Function to display my front webpage
def home(request):
    return render(request, 'frontend/index.html')