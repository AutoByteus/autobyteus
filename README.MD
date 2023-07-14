generating GRPC server code


```javascript
python -m grpc_tools.protoc -I./src/proto --python_out=./src/proto --grpc_python_out=./src/proto ./src/proto/grpc_service.proto
```

 \n Import generated code

```javascript
import src.proto.grpc_service_pb2 as automated_coding_workflow_pb2
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc
```



For local development, we can install grpccurl

<https://github.com/fullstorydev/grpcurl>

If you already have go, then do the following

```javascript
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
```

```javascript
grpcurl -d '{}' -proto autobyteus/src/proto/grpc_service.proto -plaintext localhost:50051 automatedcodingworkflow.AutomatedCodingWorkflowService/StartWorkflow
{
"result": "Workflow started successfully"
}
```



```javascript
pytest  tests/source_code_tree/test_source_code_parser.py
```

```python
python src/app.py --mode graphqlserver --host 127.0.0.1 --port 8000
```


