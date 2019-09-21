# zhmensa-backend
REST API for Mensa Zürich Website + App

## Install instructions
1. Install Mongo DB

  ``sudo apt install -y mongodb``
  
2. Install Pip Dependency

  ``pip install -r requirements.txt``

## Run REST Server
``python run.py``
### Common used API Links

> **PATH**: /api/getMensaForTimespan?start=\<start>&end=\<end>
>  
> **Request Type**: GET
>
> \<start> = YYYY-MM-DD (e.g. 2019-09-23)
> 
> \<end> = YYYY-MM-DD (e.g 2019-09-28)
  
