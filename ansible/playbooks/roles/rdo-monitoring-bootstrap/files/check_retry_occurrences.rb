#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
#  Credit and thanks for workflow implementation to Yelp:
#  https://github.com/Yelp/sensu_handlers/blob/master/files/num_occurrences_filter.rb

module Sensu::Extension
  class CheckRetryOccurrences < Filter

    STOP_PROCESSING  = 0
    ALLOW_PROCESSING = 1

    def name
      'check_retry_occurrences'
    end

    def description
      "Evaluates the event 'occurences' field against a check's "\
      "'occurrences' or 'retry_interval' fields. "\
      "Will filter if event occurrences is equal to the check's 'occurrences' "\
      "or if it is divisible (modulo) by retry_interval."
    end

    def run(event)
      begin
        rc, msg = filter_by_retry_occurrences(event)
        yield msg, rc
      rescue => e
        # filter crashed - let's pass this on to handler
        yield e.message, ALLOW_PROCESSING, "check_retry_occurrences filter error"
      end
    end

    def filter_by_retry_occurrences(event)
      event_occurrences = event[:occurrences].to_i
      check_occurrences = event[:check][:occurrences].to_i
      retry_occurrences = event[:check][:retry_occurrences].to_i || check_occurrences

      # This might not be a "retry" but a first notification
      if event_occurrences == check_occurrences
        return ALLOW_PROCESSING, "event occurrences matches check occurrences"
      end

      # If we're here, we're "retrying", check if it matches retry_occurrences
      if event_occurrences % retry_occurrences == 0
        return ALLOW_PROCESSING, "event occurrences matches retry occurrences"
      end
      
      return STOP_PROCESSING, "event occurrences does not match check or retry occurrences"
    end
  end
end
