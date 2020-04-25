## Synopsis
First version presently is centralize

## Code Example


## Motivation

To understand blockchain and for fun

## Installation
python 3.6+
To run locally with minikube

```bash
brew install minikube
minikube start
eval $(minikube docker-env)
```

## Usage locally
```bash
python node.py will default port 5000 first node
python node.py -p <port> to run another node in different port
```

## Usage minikube 
```bash
docker build -t lightchain .
kubectl apply -f lightchain-deployment.yaml
minikube service lightchain-service
```
The last line will open the webpage to use the blockchain UI.


## API Reference

## Tests

None now

## Contributors
Alexson Pel

## License

