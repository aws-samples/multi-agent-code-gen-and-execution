FROM public.ecr.aws/lambda/python:3.13.2025.01.07.15
                            RUN pip install requests
                            COPY home_network_agent_lambda_function.py app.py
                            CMD ["app.lambda_handler"]
                            