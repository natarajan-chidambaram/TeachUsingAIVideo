FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Baked in at build time: Vite inlines import.meta.env.VITE_* into the bundle.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

RUN npm install -g serve

EXPOSE 3000

# -s rewrites unknown paths to index.html so client-side routes work.
CMD ["serve", "-s", "dist", "-l", "3000"]
