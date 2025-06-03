FROM node:18-alpine

WORKDIR /app

RUN npm init -y && npm install express cors

COPY mcp-proxy.js .

EXPOSE 3000

CMD ["node", "mcp-proxy.js"]
