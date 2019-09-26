# jcomparison
Job times compare tool

```
cd jcomparison/
docker build . -t compare
docker run -d --name comparison -p 5000:5000 compare
```

or
```
docker run -d --name comparison -p 5000:5000 sshnaidm/jcomparison
```

enter http://localhost:5000
