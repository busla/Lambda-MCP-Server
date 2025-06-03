ARG LAMBDA_ARCHITECTURE=x86_64
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements and install Python dependencies
COPY server/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt

# Copy application code
COPY server/ ${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"]
