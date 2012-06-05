<h1>GitZen</h1>

<p>This is a web application built using Django that links Zendesk and Github for easier developer management.</p>

<h3>Deploying the application to Heroku (on Ubuntu)</h3>

<ol>
<li>Make an account on http://www.heroku.com/</li>
<li>Install the Heroku toolbet using the command "wget -qO- https://toolbelt.heroku.com/install.sh | sh".</li>
<li>Login to Heroku by running the command "heroku login" and filling out the requested credentials.</li>
<li>Install python and virtualenv. (A guide for this can be found at http://docs.python-guide.org/en/latest/starting/install/linux/)</li>
<li>Install a version of Postgres from http://www.postgresql.org/download/ so testing can be done locally.</li>
<li>Clone the GitZen repo with the command "git clone git://github.com/FriedRice/GitZen.git".</li>
<li>Change directories to the newly cloned GitZen directory and setup a virualenv using the command "virtualenv venv --distribute".</li>
<li>Activate the virtualenv with the command "source venv/bin/activate". (You must source the virtualenv environment for each terminal session where you wish to run your app.)</li>
<li>Run the command "sudo apt-get install libpq-dev python-dev" to install the necessary packages that allow for the installation of psycopg2 (Postgresql support for python) in the following step.</li>
<li>Install the required packages for GitZen and Heroku with pip by using the command "pip install -r requirements.txt".</li>
<li>Create the app on Heroku's Cedar stack by running the command "heroku create --stack cedar".</li>
<li>Deploy the app with the command "git push heroku master".</li>
<li>The command "heroku logs" can be used to view the logs of the app if desired, and the command "heroku open" can be used to visit the app on the web.</li>
<li>In order to conduct one-off admin processes for the app in django, preface the commands with "heroku run". An example of this would be syncing the databases in django by using the command "heroku run python manage.py syncdb".</li>
</ol>
