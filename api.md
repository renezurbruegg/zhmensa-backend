
### API Path   `/api/polls`
### Request Type: `POST`
Returns all Poll objects matching the id's in post request body.
***
### API Path   `/api/poll/<id>`
### Request Type: `GET`
Returns the poll for the given id
***
### API Path   `/api/polls/vote/<id>`
### Request Type: `POST`
Performs a vote action on the given Poll.
### Request Body:
    "votes" : [
        {
            "mensaId": "<mensaId>",
            "menuId": "<menuId>",
            "voteType": "<positive/negative>"
        } ,
        { ... }
    ],
    "update": <true/false>`
***
### API Path   `/api/polls/update/<id>`
### Request Type: `POST`
Updates a given Poll.

Payload Example:

    {
	       "title": "new Vote",
	       "weekday":0,
	       "mealType":"lunch",

	       "options": [
	       {
	       "mensaId": "testMensa", "menuId": "testMenu"

	       },
	       {
	          "mensaId": "testMensa", "menuId": "testMenu2"
	       }
	       ]
    }
***
### API Path   `/api/polls/create`
### Request Type: `POST`
Creates a new Poll for the given mensa id's
Payload Example:
    {
	"title": "new Vote",
	"weekday":0,
	"mealType":"lunch",
	"options": [
		{
			"mensaId": "testMensa", "menuId": "testMenu"

		},
		{
			"mensaId": "testMensa", "menuId": "testMenu2"
		}
		]
    }
***
### API Path   `/api/getAllMensas`
### Request Type: `GET`
Returns all mensas for the actual week
***
### API Path   `/api/getAllMensas`
### Request Type: `GET`
Returns all mensas for the actual week
***