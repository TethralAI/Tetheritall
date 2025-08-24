#!/bin/bash
set -o xtrace

# EKS Node Userdata Script
# Bootstrap script for EKS worker nodes

# Update system
yum update -y

# Install additional packages
yum install -y amazon-ssm-agent htop iotop

# Enable SSM Agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Configure EKS bootstrap
/etc/eks/bootstrap.sh ${cluster_name} ${bootstrap_arguments}

# Configure Docker (if needed for legacy workloads)
systemctl enable docker
systemctl start docker

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configure log rotation
cat << 'EOF' > /etc/logrotate.d/kubernetes
/var/log/pods/*/*.log {
    rotate 5
    daily
    compress
    missingok
    notifempty
    maxage 30
    copytruncate
}
EOF

# Set up custom metrics collection
cat << 'EOF' > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
    "metrics": {
        "namespace": "EKS/Tethral",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/eks/tethral/system",
                        "log_stream_name": "{instance_id}/messages"
                    },
                    {
                        "file_path": "/var/log/dmesg",
                        "log_group_name": "/aws/eks/tethral/system",
                        "log_stream_name": "{instance_id}/dmesg"
                    },
                    {
                        "file_path": "/var/log/secure",
                        "log_group_name": "/aws/eks/tethral/security",
                        "log_stream_name": "{instance_id}/secure"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Configure kubelet with custom settings
cat << 'EOF' > /etc/kubernetes/kubelet/kubelet-config.json
{
    "kind": "KubeletConfiguration",
    "apiVersion": "kubelet.config.k8s.io/v1beta1",
    "address": "0.0.0.0",
    "port": 10250,
    "readOnlyPort": 0,
    "cgroupDriver": "systemd",
    "hairpinMode": "hairpin-veth",
    "serializeImagePulls": false,
    "featureGates": {
        "RotateKubeletServerCertificate": true
    },
    "serverTLSBootstrap": true,
    "authentication": {
        "x509": {
            "clientCAFile": "/etc/kubernetes/pki/ca.crt"
        },
        "webhook": {
            "enabled": true,
            "cacheTTL": "2m0s"
        },
        "anonymous": {
            "enabled": false
        }
    },
    "authorization": {
        "mode": "Webhook",
        "webhook": {
            "cacheAuthorizedTTL": "5m0s",
            "cacheUnauthorizedTTL": "30s"
        }
    },
    "registryPullQPS": 10,
    "registryBurst": 20,
    "eventRecordQPS": 5,
    "eventBurst": 10,
    "kubeAPIQPS": 10,
    "kubeAPIBurst": 10,
    "systemReserved": {
        "cpu": "100m",
        "memory": "100Mi",
        "ephemeral-storage": "1Gi"
    },
    "kubeReserved": {
        "cpu": "100m",
        "memory": "100Mi",
        "ephemeral-storage": "1Gi"
    }
}
EOF

# Install kubectl for debugging
curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.29.0/2024-01-04/bin/linux/amd64/kubectl
chmod +x ./kubectl
mv ./kubectl /usr/local/bin

# Setup log rotation for container logs
mkdir -p /etc/logrotate.d
cat << 'EOF' > /etc/logrotate.d/docker-containers
/var/lib/docker/containers/*/*.log {
    rotate 5
    daily
    compress
    missingok
    delaycompress
    copytruncate
    maxsize 10M
}
EOF

# Configure kernel parameters for Kubernetes
cat << 'EOF' > /etc/sysctl.d/99-kubernetes.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
vm.overcommit_memory = 1
kernel.panic = 10
kernel.panic_on_oops = 1
EOF

sysctl --system

# Load required kernel modules
modprobe br_netfilter
echo 'br_netfilter' > /etc/modules-load.d/br_netfilter.conf

# Install additional monitoring tools
yum install -y prometheus-node-exporter

# Configure node-exporter
systemctl enable prometheus-node-exporter
systemctl start prometheus-node-exporter

# Signal completion
/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource AutoScalingGroup --region ${AWS::Region} || true

echo "EKS Node bootstrap completed successfully"
