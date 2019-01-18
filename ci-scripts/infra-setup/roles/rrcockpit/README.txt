Adding changes to the json files
-------------------------------------------
Setting up the development environment
> cd files
> ./development_script.sh --help

Exporting/Importing local grafana changes

> cd files/grafana

Generate the API key 'grafana.key' if nis not already present

> ./create-api-key --key-name "foo" > grafana.key

Dump grafana UI to json files

> ./export-grafana.py

Dump json files to grafana UI

> ./import-grafana.py

Testing and changing telegraf scripts
------------------------------------------

First install the requirements

> pip install --user -r files/telegraf/requirements.txt

Then you can do a telegraf test on them for example for launchpad

> cd files/telegraf
> PATH=.:$PATH telegraf --test --config telegraf.d/launchpad.conf

The scripts are very standalone so you can directly execute them

> cd files/telegraf
> ./launchpad_bugs.py --tag promotion-blocker

If you see errors with "telegraf --test" like
'Error in plugin [inputs.exec]: metric parse error: expected field at offset 497'
It means that there is stuff generatd by the python script at character 497
that telegraf cannot parse

Best way to fix those is dumping with the python script with the options from
telegraf to a file and doing with "vim" a ":goto 497" to go to the character
from this you can iterate until "telegraf --test" passes.
