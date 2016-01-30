# Deploy RabbitMQ, Redis, Sensu and Uchiwa
include ::rabbitmq
include ::redis

class { 'sensu':
  subscriptions => ['default', 'master']
}

include ::uchiwa
Service['sensu-api'] -> Service['uchiwa']
Yumrepo['sensu'] -> Package['uchiwa']
