# zhmensa-backend
REST API for Mensa Zürich Website + App

[![Build Status](https://www.travis-ci.org/renezurbruegg/zhmensa-backend.svg?branch=master)](https://www.travis-ci.org/renezurbruegg/zhmensa-backend)
## Install instructions
1. Install Mongo DB

  ``sudo apt install -y mongodb``
  
2. Install Pip Dependency

  ``pip install -r requirements.txt``

3. Make sure MongoDB is running on Port 27017.

## Menu Crawler
The file menuCrawler.py contains the logic to crawl every Menu from every Mensa for the current week. 

It will store all parsed menus in the collection "menus" inside the "zhmensa" database. 

This script should be run periodically to keep updating the stored menus.

Execute it by typing:

``python menuCrawler.py``

## REST Server
  The REST server gets started by executing the run.py script.
  
``python run.py``

It provides different routes that will return Menus and Polls in JSON format. 

For further information check out the 

[API Documentation](./api.md)

