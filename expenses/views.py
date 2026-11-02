from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ExpenseSerializer, RegisterSerializer
from django.shortcuts import render
from rest_framework import viewsets, permissions, generics, filters
from .models import Expense
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class ExpenseViewSet(viewsets.ModelViewSet):
    # queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_class = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "date"]
    search_fields = ["description", "place"]
    ordering_fields = ["date", "amount"]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset()
        by_category = qs.values("category").annotate(total=Sum("amount")).order_by("-total")
        by_month = (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        return Response({
            "total": qs.aggregate(t=Sum("amount"))["t"] or 0,
            "by_category": list(by_category),
            "by_month": list(by_month),
        }) 

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    