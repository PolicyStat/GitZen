# GitZen

This is a web application built using Django that links Zendesk and Github for
easier developer management.


### Setting up the environment for Heroku deployment (on Ubuntu)

1. Make a Heroku account on their [website](http://www.heroku.com/).

2. Install the Heroku toolbet using the command
	>`wget -qO- https://toolbelt.heroku.com/install.sh | sh`

3. Login to Heroku by running the command
	>`heroku login`

	and filling out the requested credentials.

4. Install python and virtualenv. (A guide for this can be found
[here](http://docs.python-guide.org/en/latest/starting/install/linux/))

5. Install a version of Postgres from
[here](http://www.postgresql.org/download/) so testing can be done locally.

6. Clone the GitZen repo with the command
	>`git clone git://github.com/PolicyStat/GitZen.git`

7. Change directories to the newly cloned GitZen directory and setup a virualenv
using the command
	>`virtualenv venv --distribute`

8. Activate the virtualenv with the command
	>`source venv/bin/activate`
		
	You must source the virtualenv environment for each terminal session where
you wish to run your app.

9. Run the command
	>`sudo apt-get install libpq-dev python-dev`

	to install the necessary packages that allow for the installation of
psycopg2 (Postgresql support for python) in the following step.

10. Install the required packages for GitZen and Heroku with pip by using the
command
	>`pip install -r requirements.txt` 


### Deploying the application to Heroku (on Ubuntu)

1. Create the app on the Heroku Cedar stack by running the command
	>`heroku create --stack cedar`

2. Deploy the app with the command
	>`git push heroku master`

3. Using the command
	>`heroku config:add`

	add the configuration constants for the Django secret key for the GitZen
project, the GitHub OAuth client ID and client secret for GitZen, and the SMTP
host username and password for the Amazon SMTP server. These must be defined
under the variable names `SECRET_KEY`, `CLIENT_ID`, `CLIENT_SECRET`,
`SMTP_USER`, and `SMTP_PASSWORD` respectively.

4. Sync the database for Django on Heroku by runing the command
	>`heroku run python manage.py syncdb`

	and then use the command
	>`heroku run python manage.py createcachetable enhancement_cache`

	to create the database table used for the cache in the application.

5. The command
	>`heroku logs`

	can be used to view the logs of the app if desired, and the command
	>`heroku open`

	can be used to visit the app on the web.

6. In order to conduct one-off admin processes for the app in Django, preface
the commands with
	>`heroku run`

	An example of this would be opening the Django shell on Heroku by using the
command
	>`heroku run python manage.py shell`


### Configuration Instructions

GitZen works by creating groups of users that share the same API access data for
GitHub and Zendesk. Each one of these groups has one group superuser that is
created at the creation of the group, and this user is the only user that can
add new users to their group in addition to changing the API acces settings for
the group. The following instructions detail how to create a new group and group
superuser for GitZen:

1. Go to the [GitZen website](http://gitzen.herokuapp.com) on Heroku.

2. Click on the "Create New User Group" button on the login screen.

3. Begin filling out the fields under the "Group Superuser" header to set up the
account settings for the group superuser account. The "Group Superuser
Username", "Password", and "Password Confirmation" are the basic login
information for the group superuser.

4. For the "Time Zone (UTC Offset)" field, enter in the UTC offset of the
superuser's local time zone in order to adjust the dates and times of the
application to the proper times for the superuser's location. This offset only
effects the superuser's view of the application as each user will be able to set
their own UTC offset to adjust the dates and times of the application for their
view. The number value of the offset should be prefaced with a "+" or "-" to
indicated whether the offset is ahead or behind UTC time (i.e. "-4" or "+9").

5. For the "View Type" field in the form, select whether the home page should
be presented from a GitHub-centered or Zendesk-centered user perspective for the
superuser. By selecting one of these options, the home page will be set up to
provide information in a more useful way depending on whether a GitZen user is
using the application from a GitHub perspective or a Zendesk perspective. 

6. Now, you can begin filling out the fields under the "Group API Access Settings"
header to set up the API access settings that will be used by every user in the
group. The following steps detail what exact information should be entered in
each of these fields.

7. For the "Product Name" field, enter in the name of the product whose
enhancements will be tracked by GitZen. This field is purely a label to be used
by the application and is not used in accessing either the GitHub or Zendesk
APIs.

8. In order to use GitHub issue information in GitZen, each group must provide
information on the GitHub repository from which issue information should be
monitored. This access information consists of a GitHub organization name and
repository name associated with the desired issue information, and those
parameters should be filled into the "GitHub Organization" and "GitHub
Repository" fields respectively. If the repository is under a user account
rather than an organization, provide the username of that account in the
organization field instead.

9. In order to use Zendesk ticket information in GitZen, each group must provide
a set of access information from a Zendesk account linked to the tickets that
should be monitored. The first information required to access this data is a
Zendesk user email which should be filled into the "Zendesk User Email" field of
the form. The other three bits of Zendesk access information needed are more
specific and are covered in the following steps.

10. In order to allow API token access to the Zendesk account, "Token Access"
must be enabled. This option can be found by logging into Zendesk with an
account that has administrator level credentials and looking under
"Settings"->"Channels"->"API". After clicking "edit" and checking the "Token
Access" box, copy the displayed API token and paste it into the "Zendesk API
Token" field in the form.

11. For the "Zendesk URL Subdomain" field in the form, enter in the unique URL
subdomian that comes up after logging into the Zendesk account associated with
the desired ticket information (The URL will most likely be in the format
"\{subdomain\}.zendesk.com").

12. For the "Zendesk Ticket Association Field ID" field in the form, the ID
number of the field that holds the external ticket association data for each
Zendesk ticket must be found. In order to find this ID number, first look up the
ID number of a Zendesk ticket from the desired account that has this ticket
association field on it. Then open up a command terminal and enter in the
following command, substituting the parameters surrounded by braces with the
information from the desired Zendesk account and substituting the `id` parameter
with the ticket ID number that was just looked up:
	>`curl https://{zendesk_url_subdomain}/api/v2/tickets/{id}.json -u
	>{email_address}/token:{api_token}`

	From the output of this command, look for the dictionary key "fields", and
within the dictionaries listed for the value of this key, look for the one with
the value of the "value" key matching the value of the ticket association field
of the Zendesk ticket that was looked up for this process. In the same
dictionary as this "value" pair, the number value for the "id" key is the ID
number that must be entered into the "Zendesk Ticket Association Field ID" field
in form.

13. Check to see that all fields in the form are filled out accurately, and then
click the "Submit" button to create a group and group superuser with the given
information.

13. Once the group has been created, the next page will instruct you to
authorize GitZen on GitHub for the newly created group by clicking the "GitHub
Authorization" button. Click this button to start the authorization process, and
after it is completed (either automatically or by following the GitHub
instructions), a confirmation page will come up.

14. On this confirmation page from the GitHub OAuth authorization, you will be
prompted to build the cache index with the enhancement data for the group for
the first time. Click on the "Build Cache Index" button to start this process,
and once the process has finished (it may take up to 20 seconds to complete), a
confirmation page will come up that will say if the cache was successfully built
or if there was some error in the process. Either way, click the "Go to
Superuser Home" button on the confirmation page to go to the superuser
interface.

15. On the group superuser home page, you can now create users that will be
added to the group, modify users already in the group, or modify the API access
settings for the group. Also, you can click the "Return to Normal View" button
at the top to go to the normal user home page for your group, or you can click
the "Reset Cache" button at the top to completely flush and reset the cache
index for the group. Once you have created a user from this interface, that user
will be emailed their login information and will be able to login to the
application to view the enhancement tracking data for the group.
