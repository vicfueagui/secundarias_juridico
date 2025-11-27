from django.urls import path

from incidencias import views

app_name = "incidencias"

urlpatterns = [
    path("", views.IncidenciaListView.as_view(), name="incidencia-list"),
    path("nueva/", views.IncidenciaCreateView.as_view(), name="incidencia-create"),
    path("<int:pk>/reporte/", views.IncidenciaReporteUpdateView.as_view(), name="incidencia-reporte-editar"),
    path("<int:pk>/reporte/pdf/", views.IncidenciaReportePDFView.as_view(), name="incidencia-reporte-pdf"),
]
