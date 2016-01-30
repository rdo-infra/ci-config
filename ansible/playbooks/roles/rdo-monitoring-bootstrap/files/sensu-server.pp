# Deploy RabbitMQ, Redis, Sensu and Uchiwa
include ::rabbitmq
include ::redis

class { 'sensu':
  subscriptions => ['default', 'master']
}

# Setup filter so notifications go out no more than one every 30 minutes
# TODO: Add "filters" to sensu::init upstream ?
sensu::filter { 'recurrences-30':
  attributes => {
    'occurrences' => "eval: value == 1 || value % 30 == 0"
  }
}

sensu::filter { 'recurrences-60':
  attributes => {
    'occurrences' => "eval: value == 1 || value % 60 == 0"
  }
}

include ::uchiwa
Service['sensu-api'] -> Service['uchiwa']
Yumrepo['sensu'] -> Package['uchiwa']
