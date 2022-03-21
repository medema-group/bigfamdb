gunicorn -b=0.0.0.0:8286 --workers=2 "start_server:bigfam()"
