# ngUML API Mapping Framework
## Description
**This project is made as a backbone for my master thesis for ICT in Business and the Public Sector and is currently still very much work in progress.** 
The project aims to connect applications to each other through their APIs in a generic way.
The main (research) purpose was to connect the ngUML project [[1]](#1) to third-party low-code vendors in a generic way. 
But this tool can be used to make a connection between any pair applications!

## Features
* Based on OpenAPI documents
* Full OpenAPI generation by simply calling your APIs
* API visualisation and connection in the easy to use the High Level Flow editor
* API connection recommendations powered by Machine Learning and Natural Language processing
* Full custom JSON visualisation and simple to make connections between JSON data element the Low Level Mapping Interface
* Immediately synchronise the configured API connections with the build in Sync Server
* No SDK needed, this is generated based on your OpenAPI document or the generated OpenAPI document
* Possibility to use custom python code with a provided boilerplate in the interface for complex connections

## Screenshots
![MF_AddEndpointWithExamples](https://user-images.githubusercontent.com/24565835/198352124-064a1b10-57f8-409b-9e93-df43bad62dbe.png)
OpenAPI document generation by simply calling the API

![MF_OpenAPIResult](https://user-images.githubusercontent.com/24565835/198352159-90d4424f-d780-4d58-b174-900b2fe20dbd.png)
OpenAPI document results

![HLM_demo](https://user-images.githubusercontent.com/24565835/198352021-69c5ddf5-fd9f-434c-a154-f7eba43220fb.png)
High Level Flow editor with all available APIs within each application

![LLM_demo](https://user-images.githubusercontent.com/24565835/198352056-05d1d879-1b2c-453a-8ef1-729bc02e5c3a.png)
Low Level Flow editor showing the JSON data schema, the shape of the JSON that that API is going to respond or request 

![SS_overview](https://user-images.githubusercontent.com/24565835/198352187-11a2e47c-4de8-4afa-b320-b000538b4985.png)
Synchronization server to automatically transport the data between the applications

## Usage
The setup relies on docker and docker-compose
If you do not already have that you can find a tutorial on how to install it [here](https://docs.docker.com/get-docker/).

Then build the docker images by running:
(depending on your way of installing docker and docker-compose you may need to add `sudo` in front of the commands)

`docker compose build`

This can take up to 10 minutes to finish. After building you start the whole socker stack by running:

`docker compose up`

When this is running without errors you can reach the frontend on:

`http://localhost:3000`

## To Do
* Finish documentation and type hinting
* Try neural network as the provider for the ML model
* Add publication of thesis, when available, for added context
* Writing tests

## References
<a id="1">[1]</a>
Ramackers, G. J., Griffioen, P. P., Schouten, M. B., & Chaudron, M. R. (2021, October). From prose to prototype: Synthesising executable uml models from natural language. In 2021 ACM/IEEE International Conference on Model Driven Engineering Languages and Systems Companion (MODELS-C) (pp. 380-389). IEEE.