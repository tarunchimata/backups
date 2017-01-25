import urllib, urllib2
import os, os.path
import json
import logging
import base64

from prometheus_client import CollectorRegistry, Gauge, Summary, push_to_gateway
from prometheus_client.handlers.basic_auth import handler as http_basic_auth_handler

from backups.exceptions import BackupException
from backups.notifications import backupnotification
from backups.notifications.notification import BackupNotification

@backupnotification('prometheus')
class Prometheus(BackupNotification):
    def __init__(self, config):
        BackupNotification.__init__(self, config, 'prometheus')
        try:
            self.url = config.get('prometheus', 'url')
        except:
            self.url = config.get_or_envvar('defaults', 'url', 'PUSHGW_URL')
        try:
            self.username = config.get('prometheus', 'username')
        except:
            self.username = config.get_or_envvar('defaults', 'username', 'PUSHGW_USERNAME')
        try:
            self.password = config.get('prometheus', 'password')
        except:
            self.password = config.get_or_envvar('defaults', 'password', 'PUSHGW_PASSWORD')
        self.notify_on_success = True
        self.notify_on_failure = False

    def notify_success(self, source, hostname, filename, stats):
        registry = CollectorRegistry()

        s = Summary('backup_size', 'Size of backup file in bytes', registry=registry)
        s.observe(stats.size)
        s = Summary('backup_dumptime', 'Time taken to dump and compress/encrypt backup in seconds', registry=registry)
        s.observe(stats.dumptime)
        s = Summary('backup_uploadtime', 'Time taken to upload backup in seconds', registry=registry)
        s.observe(stats.uploadtime)
        g = Gauge('backup_retained_copies', 'Number of retained backups found on destination', registry=registry)
        g.set(stats.retained_copies)
        g = Gauge('backup_timestamp', 'Time backup completed as seconds-since-the-epoch', registry=registry)
        g.set_to_current_time()

        def auth_handler(url, method, timeout, headers, data):
            return http_basic_auth_handler(url, method, timeout, headers, data, self.username, self.password)

        push_to_gateway(self.url, job=source.id, registry=registry, handler=auth_handler)

        logging.info("Pushed metrics for job '%s' to gateway (%s)" % (source.id, self.url))