from django.urls import path

from apps.documents.views import DocumentDownloadView, DocumentUploadView

urlpatterns = [
    path("documents/", DocumentUploadView.as_view(), name="document-list-create"),
    path(
        "documents/<uuid:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
]
