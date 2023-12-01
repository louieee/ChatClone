<h2>ChatClone</h2>

<h3>SET UP INSTRUCTIONS</h3>
<ul>
</ul>
<li>Setup virtual environment</li> 
<li>Run <code>pip install -r requirements.txt </code> to install the dependencies.</li>
<li>Run <code>python manage.py makemigrations</code> to generate a database migration file.
<li>Run <code>python manage.py migrate</code> to migrate the commands in the migration file to the database.</li>
<li>Run <code>python manage.py collectstatic -y</code> to generate needed static files and gather them in the static root folder</li>
<li>Run <code>python manage.py runserver </code> to start the web server on port 8000</li>
<li>Navigate to <a href="http://localhost:8080/docs">http://localhost:8080/docs</a> to view the documentation and also test the endpoints
<li>Go to your terminal and type <code>python test.py</code>, This would ask you to input the channel name and the user id, 
this allows you to connect different users to different channels and monitor how they receive receive the websocket signals </li>
<li>While testing the endpoints on swagger, watch how the signals are being sent</li>

<h3>NOTE:</h3>
<li>I used <code>Models</code> instead of <code>Entity</code> because django recognizes models.py.</li>
<li>I could not write tests because the deadline was short. All these was done within a day</li>
<li>I did not write a lot of comments unless where necessary.</li>
<li>I did not use .env file because this is just an assignment.</li>

<h3>Stack Used</h3>
<li>Django, Django Rest Framework, Django Channels and Swagger</li>
<small>Please refer to the <code>requirements.txt</code> for more information</small>