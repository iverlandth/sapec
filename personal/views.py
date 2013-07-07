#encoding:utf-8
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from organizacion.models import Unidades, Cargos, Funciones
from personal.form import EmpleadoForm, ProfesionForm, Contrato, AsistenciaForm, ObservacionForm, PermisoForm
from personal.models import Empleados, contratacion, Asistencia, Entrada, Salida, Observacion, Permiso, moviidad


from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required

from django.conf import settings

from datetime import datetime

import ho.pisa as pisa
import cStringIO as StringIO
import cgi
from django.template.loader import render_to_string
import os



@login_required(login_url='/user/login')
def home(request):
    return render_to_response('index_personal.html', context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def new_empleado(request, cod_cargo):
    #cargo = Cargos.objects.filter(id = cod_cargo)
    cargo = Cargos.objects.get(pk = cod_cargo)
    if request.method == 'POST' :
        formulario = EmpleadoForm(request.POST, request.FILES)
        if formulario.is_valid() :
            carnet = formulario.cleaned_data['ci']
            nombre = formulario.cleaned_data['nombre']
            paterno = formulario.cleaned_data['paterno']
            email = formulario.cleaned_data['email']
            emple = Empleados.objects.filter(ci = carnet)
            if(emple):
                return HttpResponseRedirect('/contrato/new/'+str(carnet)+"/"+str(cod_cargo)+"/")
            else:
                newuser = User.objects.create_user(carnet, email, carnet)
                formulario.save()
                per = Empleados.objects.get(ci = carnet)
                per.usuario_id=newuser.id
                per.save()
                newuser.is_active = 0
                newuser.first_name = nombre
                newuser.last_name = paterno
                newuser.save()
                #formulario.save()
                return HttpResponseRedirect('/contrato/new/'+str(carnet)+"/"+str(cod_cargo)+"/")
    else:
        formulario = EmpleadoForm()
    return render_to_response('personal/new_empleado.html', {'formulario' :formulario, 'cargo' :cargo}, context_instance=RequestContext(request))

@login_required(login_url='/user/login')
def option_empleado(request):
    empleado=Empleados.objects.all()
    contratos = contratacion.objects.exclude(fecha_salida__lte = datetime.today())
    return render_to_response('personal/option_empleado.html', {'empleados' :empleado, 'contratos':contratos}, context_instance=RequestContext(request))

@login_required(login_url='/user/login')
def update_empleado(request, empleado_id):
    empleado = get_object_or_404(Empleados, pk = empleado_id)
    if request.method == 'POST':
        formulario = EmpleadoForm(request.POST, request.FILES, instance = empleado)
        if formulario.is_valid():
            formulario.save()
            return HttpResponseRedirect('/personal/option')
    else:
        formulario = EmpleadoForm(instance = empleado)
    return render_to_response('personal/update_empleado.html', {'formulario' :formulario}, context_instance=RequestContext(request))

@login_required(login_url='/user/login')
def new_profesion(request):
    if request.method == 'POST' :
        formulario = ProfesionForm(request.POST, request.FILES)
        if formulario.is_valid() :
            formulario.save()
            return HttpResponseRedirect('/personal')
    else:
        formulario = ProfesionForm()
    return render_to_response('personal/new_profesion.html', {'formulario' :formulario}, context_instance=RequestContext(request))

#CONTRATACION
@login_required(login_url='/user/login')
def cargos_contrato(request):
    unidad = Unidades.objects.all()
    cargo = Cargos.objects.all()
    return render_to_response('personal/cargo_contrato.html', {'cargos' :cargo, 'unidades' :unidad}, context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def new_contrato(request, empleado_ci, cargo_id):
    cargo = Cargos.objects.get(pk = cargo_id)
    empleado = Empleados.objects.get(ci = empleado_ci)
    if request.method == 'POST' :
        formulario = Contrato(request.POST, request.FILES)
        if formulario.is_valid() :
            empleado = Empleados.objects.get(ci=int(empleado_ci))
            id =empleado.id
            fecha_fin =formulario.cleaned_data['fecha_fin']
            sueldo=formulario.cleaned_data['sueldo']
            descuento=formulario.cleaned_data['descuento']
            cargo=int(cargo_id)
            c = contratacion.objects.create(fecha_entrada=datetime.today(),
                                        fecha_salida=fecha_fin,
                                        estado='ACTIVO',
                                        sueldo=sueldo,
                                        descuento=descuento,
                                        empleado_id=id,
                                        cargo_id=cargo,
                                        )

            return HttpResponseRedirect('/contrato/show/'+str(c.id)+'/'+str(0)+'/')
    else:
        formulario = Contrato()
    return render_to_response('personal/new_contratacion.html', {'formulario' :formulario, 'empleado_ci':empleado_ci, 'cargo' :cargo, 'empleado' :empleado}, context_instance=RequestContext(request))

def show_contrato(request, cod_contrato, pdf = 0) :
    contrato = get_object_or_404(contratacion, pk = cod_contrato)
    cargo = Cargos.objects.get( pk = contrato.cargo_id)
    unidad = Unidades.objects.get(pk = cargo.unidad_id)
    funciones = Funciones.objects.filter(cargo_id = cargo.id)
    unidad.descripcion = unidad.descripcion[0 : 100] + '...'
    cargo.descripcion = cargo.descripcion[0 : 100] + '...'
    empleado = Empleados.objects.get(pk = contrato.empleado_id)
    if int(pdf) :
        html = render_to_string('personal/show_contrato_pdf.html', {'pagesize':'Letter',
                                                                'cargo' :cargo,
                                                                'unidad' :unidad,
                                                                'contrato' :contrato,
                                                                'empleado' :empleado,
                                                                'funciones' :funciones},
                                context_instance=RequestContext(request))
        return generar_pdf(html)
    else:
        return render_to_response('personal/show_contrato.html', {'cargo' :cargo,
                                                                  'unidad' :unidad,
                                                                  'contrato' :contrato,
                                                                  'empleado' :empleado,
                                                                  'funciones' :funciones},
                                  context_instance=RequestContext(request))


def new_asistencia(request):
    if request.method == 'POST' :
        formulario = AsistenciaForm(request.POST, request.FILES)
        if formulario.is_valid() :
            carnet = formulario.cleaned_data['ci']
            if Empleados.objects.filter(ci = carnet) :
                emple = Empleados.objects.get(ci = carnet)
                cod_emple = emple.id
                hoy = datetime.today()
                hora = hoy.strftime("%H:%M")
                if not Asistencia.objects.filter(empleado_id = emple.id, fecha = hoy) :
                    asis = Asistencia.objects.create(
                                                    fecha = hoy,
                                                    empleado_id = cod_emple
                                                    )
                else :
                    asis = Asistencia.objects.get(empleado_id = emple.id, fecha = hoy)
                #Modificar las Horas
                if hora >= "06:00" and hora <= "08:15" :
                    #Entrada mañana
                    entrada = Entrada.objects.create(
                                                    hora = hora,
                                                    obs = "MAÑANA",
                                                    asistencia = asis
                                                    )
                elif hora >= "13:00" and hora <= "14:15" :
                    #"Entrada Tarde"
                    entrada = Entrada.objects.create(
                                                    hora = hora,
                                                    obs = "TARDE",
                                                    asistencia = asis
                                                    )
                elif hora >= "12:00" and hora <= "12:59" :
                    #salida mañana
                    entrada = Salida.objects.create(
                                                    hora = hora,
                                                    obs = "MAÑANA",
                                                    asistencia = asis
                                                    )
                elif hora >= "18:00" and hora <= "22:00" :
                    #salida tarde
                    entrada = Salida.objects.create(
                                                    hora = hora,
                                                    obs = "TARDE",
                                                    asistencia = asis
                                                    )
                else:
                    if hora >= "08:16" and hora <= "11:59" :
                        #salida tarde
                        Entrada.objects.create(
                                            hora = hora,
                                            obs = "RETRASO",
                                            asistencia = asis
                                            )
                    if hora >= "14:16" and hora <= "17:59" :
                        #salida tarde
                        Entrada.objects.create(
                                            hora = hora,
                                            obs = "RETRASO",
                                            asistencia = asis
                                            )
                    if hora >= "22:01" and hora <= "05:59" :
                        #salida tarde
                        return HttpResponseRedirect('/personal/')
            else:
                return HttpResponseRedirect('/personal/asistencia/')
            return HttpResponseRedirect('/personal/asistencia/')
    else:
        formulario = AsistenciaForm()
    return  render_to_response('personal/new_asistencia.html', {'formulario' :formulario}, context_instance=RequestContext(request))

def asistecia(request, ci_emple):
    carnet = ci_emple
    if Empleados.objects.filter(ci = carnet) :
        emple = Empleados.objects.get(ci = carnet)
        cod_emple = emple.id
        hoy = datetime.today()
        hora = hoy.strftime("%H:%M")
        if not Asistencia.objects.filter(empleado_id = emple.id, fecha = hoy) :
            asis = Asistencia.objects.create(
                                            fecha = hoy,
                                            empleado_id = cod_emple
                                            )
        else :
            asis = Asistencia.objects.get(empleado_id = emple.id, fecha = hoy)
        #Modificar las Horas
        if hora >= "06:00" and hora <= "08:15" :
            #Entrada mañana
            entrada = Entrada.objects.create(
                                            hora = hora,
                                            obs = "MAÑANA",
                                            asistencia = asis
                                            )
        elif hora >= "13:00" and hora <= "14:15" :
            #"Entrada Tarde"
            entrada = Entrada.objects.create(
                                            hora = hora,
                                            obs = "TARDE",
                                            asistencia = asis
                                            )
        elif hora >= "12:00" and hora <= "12:59" :
            #salida mañana
            entrada = Salida.objects.create(
                                            hora = hora,
                                            obs = "MAÑANA",
                                            asistencia = asis
                                            )
        elif hora >= "18:00" and hora <= "22:00" :
            #salida tarde
            entrada = Salida.objects.create(
                                            hora = hora,
                                            obs = "TARDE",
                                            asistencia = asis
                                            )
        else:
            if hora >= "08:16" and hora <= "11:59" :
                #salida tarde
                Entrada.objects.create(
                                    hora = hora,
                                    obs = "RETRASO",
                                    asistencia = asis
                                    )
            if hora >= "14:16" and hora <= "17:59" :
                #salida tarde
                Entrada.objects.create(
                                    hora = hora,
                                    obs = "RETRASO",
                                    asistencia = asis
                                    )
            if hora >= "22:01" and hora <= "05:59" :
                #salida tarde
                return HttpResponseRedirect('/personal/')
    else:
        return HttpResponseRedirect('/personal/asistencia/')
    return HttpResponseRedirect('/personal/asistencia/')


@login_required(login_url='/user/login')
def new_observacion(request, cod_emple):
    if request.method == 'POST' :
        formulario = ObservacionForm(request.POST, request.FILES)
        if formulario.is_valid():

            Observacion.objects.create(
                                        tipo = formulario.cleaned_data['tipo'],
                                        descripcion = formulario.cleaned_data['descripcion'],
                                        fecha = datetime.today(),
                                        empleado_id = cod_emple,
                                        )
            #formulario.save()
            return HttpResponseRedirect('/personal/option')
    else:
        formulario = ObservacionForm()
    return  render_to_response('personal/new_observacion.html', {'formulario' :formulario}, context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def new_permiso(request, cod_emple):
    if request.method == 'POST' :
        formulario = PermisoForm(request.POST, request.FILES)
        if formulario.is_valid():
            Permiso.objects.create(
                                    descripcion = formulario.cleaned_data['descripcion'],
                                    fecha = datetime.today(),
                                    tiempo = formulario.cleaned_data['tiempo'],
                                    empleado_id = cod_emple,
                                   )
            return HttpResponseRedirect('/personal/option')
    else:
        formulario = PermisoForm()
    return  render_to_response('personal/new_observacion.html', {'formulario' :formulario}, context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def select_personal(request):
    empleado=Empleados.objects.all()
    contratos = contratacion.objects.exclude(fecha_salida__lte = datetime.today())
    return render_to_response('personal/cambio_personal.html', {'empleados' :empleado, 'contratos':contratos}, context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def cambio_cargo(request, empleado_cod):
    cargo = Cargos.objects.all()
    return render_to_response('personal/cargo_cambio.html', {'cargos' :cargo, 'empleado_cod' :empleado_cod}, context_instance=RequestContext(request))


@login_required(login_url='/user/login')
def empleado_cambio(request, cargo_cod, empleado_cod):
    contrato = contratacion.objects.get(empleado_id = int(empleado_cod), estado = 'ACTIVO')
    moviidad.objects.create(
                            contrato_id = contrato.id,
                            cargo_id = int(cargo_cod),
                            fecha = datetime.today(),
                            )
    contrato.estado = 'INACTIVO'
    contratacion.objects.create(
                                fecha_entrada = datetime.today(),
                                fecha_salida = contrato.fecha_salida,
                                estado = 'ACTIVO',
                                sueldo = contrato.sueldo,
                                descuento = contrato.descuento,
                                empleado_id = contrato.empleado_id,
                                cargo_id = int(cargo_cod),
                                )
    contrato.save()
    return HttpResponseRedirect('/personal')


def ingresar(request):
    if not request.user.is_anonymous():
        return HttpResponseRedirect('/privado')
    if request.method == 'POST':
        formulario = AuthenticationForm(request.POST)
        if formulario.is_valid:
            usuario = request.POST['username']
            clave = request.POST['password']
            #users = User.objects.get(username = usuario)
            acceso = authenticate(username=usuario, password=clave)
            if acceso is not None:
                if acceso.is_active:
                    login(request, acceso)
                    if 'next' in request.GET:
                        return HttpResponseRedirect(str(request.GET['next']))
                    else:
                        return HttpResponseRedirect('/privado')
                else:
                    return render_to_response('user/noactivo.html', context_instance=RequestContext(request))
            else:
                return render_to_response('user/nousuario.html', context_instance=RequestContext(request))
    else:
        formulario = AuthenticationForm()
    return render_to_response('user/user_login.html',{'formulario':formulario}, context_instance=RequestContext(request))



@login_required(login_url='/user/login')
def privado(request) :
    usuario = request.user
    return render_to_response('user/privado.html', {'usuario' :usuario}, context_instance=RequestContext(request))

@login_required(login_url='/user/login')
def cerrar(request):
    logout(request)
    return HttpResponseRedirect('/')


def tarjeta_empleado(request, ci_emple):
    empleado = get_object_or_404(Empleados, ci = ci_emple)
    direccion = "http://sapec.herokuapp.com/asistencia/"+str(empleado.ci)+"/"

    return render_to_response('personal/qr.html', {'empleado' :empleado, 'direccion' :direccion}, context_instance=RequestContext(request))

def view_contrato(request, cod_emple):
    q1 = get_object_or_404(Empleados, pk = cod_emple)
    hoy = datetime.today()
    q2 = contratacion.objects.get(fecha_entrada__lte=hoy, fecha_salida__gte=hoy, estado='ACTIVO', empleado_id = cod_emple)
    return HttpResponseRedirect("/contrato/show/"+str(q2.id)+"/0/")








def generar_pdf(html, numero = 1):
    # Función para generar el archivo PDF y devolverlo mediante HttpResponse
    result = StringIO.StringIO()
    links = lambda uri, rel: os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))

    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("utf-16")), result, link_callback=links)
    if not pdf.err:
        return HttpResponse(result.getvalue(), mimetype='application/pdf')
    return HttpResponse('Error al generar el PDF: %s' % cgi.escape(html))


def get_full_path_x(request):
    full_path = ('http', ('', 's')[request.is_secure()], '://',
    request.META['HTTP_HOST'], request.path)
    return ''.join(full_path)