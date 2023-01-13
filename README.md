# SpotifAI

## Description
Spotify provides a lot of different information about tracks (songs), artists and genres. This information can be
accessed via the Web API. A track doesn't have any genre information, but artists do. The project aims to
analyze tracks and find the correct genres for each track

## Google Cloud Firestore
All the necessary data is saved in a **Google Cloud Firestore**.

## Start Crawler

To start the crawler the jupiter notebook `crawler.ipynb` has to be executed. 
Before that you have to edit the `.env.dev` file to enter all the needed environment variables.
- The **Spotify** variables can all be accessed within the Spotify for Developers dashboard (https://developer.spotify.com/dashboard/applications). You have to create an account and a new project. In the project you can view the *Client ID* variable and the *Client Secret*.
- For the **last.fm** variables you have to create a last.fm account and apply for a key under (https://www.last.fm/api/authentication). Then you can access the *API Key* and the *Shared Secret*.
- Lastly the *Google Credentials* have to be given through a JSON-file. They can be fetched from the set up **Firestore**.
