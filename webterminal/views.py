from django.views.generic import View
from django.shortcuts import render_to_response,HttpResponse
from django.http import JsonResponse
from common.models import ServerGroup,CommandsSequence,Credential,ServerInfor,Log
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect,csrf_exempt
try:
    import simplejson as json
except ImportError:
    import json
from django.contrib import messages as message
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils.encoding import smart_str
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView,CreateView
from django.views.generic.detail import DetailView
from django.core.serializers import serialize
from webterminal.settings import MEDIA_URL
from django.utils.timezone import now
from common.utils import get_redis_instance
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from django.core.exceptions import  PermissionDenied
from permission.models import Permission
from django.urls import reverse_lazy
from common.views import LoginRequiredMixin
import traceback

class Index(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    template_name = 'webterminal/index.html'
    permission_required = 'common.can_connect_serverinfo'
    raise_exception = False
    login_url = reverse_lazy('admin:login')

    def get_context_data(self, **kwargs):
        context = super(Index, self).get_context_data(**kwargs)
        try:
            groups = Permission.objects.get(user__username=self.request.user.username)
        except ObjectDoesNotExist:
            return context
        context['server_groups'] = ServerGroup.objects.filter(name__in=[group.name for group in groups.groups.all()])
        return context

class SshLogPlay(LoginRequiredMixin,PermissionRequiredMixin,DetailView):
    model = Log
    template_name = 'webterminal/sshlogplay.html'
    permission_required = 'common.can_play_log'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super(SshLogPlay, self).get_context_data(**kwargs)
        objects = kwargs['object']
        context['logpath'] = '{0}{1}-{2}-{3}/{4}'.format(MEDIA_URL,objects.start_time.year,objects.start_time.month,objects.start_time.day,objects.log)
        return context

class SshTerminalMonitor(LoginRequiredMixin,PermissionRequiredMixin,DetailView):
    model = Log
    template_name = 'webterminal/sshlogmonitor.html'
    permission_required = 'common.can_monitor_serverinfo'
    raise_exception = True

class CommandExecute(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    template_name = 'webterminal/commandexecute.html'
    permission_required = 'common.can_execute_commandssequence'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super(CommandExecute, self).get_context_data(**kwargs)
        try:
            groups = Permission.objects.get(user__username=self.request.user.username)
        except ObjectDoesNotExist:
            return context
        context['commands'] = CommandsSequence.objects.filter(group__name__in=[group.name for group in groups.groups.all()])
        return context

class BatchCommandExecute(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    template_name = 'webterminal/batchcommandexecute.html'
    permission_required = 'common.can_execute_commandssequence'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super(BatchCommandExecute, self).get_context_data(**kwargs)
        try:
            groups = Permission.objects.get(user__username=self.request.user.username)
        except ObjectDoesNotExist:
            return context
        context['commands'] = CommandsSequence.objects.filter(group__name__in=[group.name for group in groups.groups.all()])
        return context

class SshTerminalKill(LoginRequiredMixin,View):
    raise_exception = True

    def post(self,request):
        if request.is_ajax():
            channel_name = request.POST.get('channel_name',None)
            try:
                data = Log.objects.get(channel=channel_name)
                if request.user.username == data.user.username or request.user.has_perm('common.can_kill_serverinfo'):
                    if data.is_finished:
                        return JsonResponse({'status':False,'message':'Ssh terminal does not exist!'})
                    else:
                        data.end_time = now()
                        data.is_finished = True
                        data.save()

                        queue = get_redis_instance()
                        redis_channel = queue.pubsub()
                        queue.publish(channel_name, json.dumps(['close']))

                        return JsonResponse({'status':True,'message':'Terminal has been killed !'})
                else:
                    return JsonResponse({'status':False,'message':'You do not have permission to kill active user action !'})
            except ObjectDoesNotExist:
                return JsonResponse({'status':False,'message':'Request object does not exist!'})