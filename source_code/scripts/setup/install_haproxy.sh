apt-get update

apt-get install haproxy socat -y

# haproxy configs
sed -i 's/^ENABLED=0/ENABLED=1/g' /etc/default/haproxy

if [[ ! -f /etc/haproxy/haproxy.cfg.orig ]]
then
  mv /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.orig
fi

# write new config
cat << EOF > /etc/haproxy/haproxy.cfg
global
    log 127.0.0.1 local0 notice
    maxconn 2000
    user haproxy
    group haproxy
    stats socket /etc/haproxy/haproxysock level admin

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    retries 3
    option redispatch
    timeout connect  5000
    timeout client  10000
    timeout server  10000

listen stats :1936
    mode http
    stats enable
    stats hide-version
    stats realm Haproxy\ Statistics
    stats uri /

listen app 0.0.0.0:80
    mode http
    stats enable
    balance roundrobin
    server server81 127.0.0.1:81 check disabled
    server server82 127.0.0.1:82 check disabled
EOF

service haproxy restart
