# syntax=docker/dockerfile:1
FROM maven:3.9.6-eclipse-temurin-17-alpine AS build
WORKDIR /app

# 1. Copy only the POM first — this layer is cached until pom.xml changes
COPY pom.xml .

# 2. Download all dependencies into the BuildKit cache mount.
#    This layer re-runs only when pom.xml changes.
RUN --mount=type=cache,target=/root/.m2 \
    mvn dependency:go-offline -q

# 3. Copy source and compile. Only this layer re-runs on source changes.
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn clean package -DskipTests -q

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
