# http-tryout-server

Simple HTTP Server who register requests and show them into a simple website for learning purposes. 

# Usage

Make a request to `/` and server will respond you with a URL, click the URL and check 
your request.

You also can add a `/json` and receive a JSON response.

# Development

Build and run with docker:

```bash
docker compose up [--build]
```

Create Tables with:

```bash
docker compose exec app poetry run flask create-db
```