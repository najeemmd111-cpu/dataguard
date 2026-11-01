# Build with Maven inside Docker, so no Java is needed on your machine.
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B -q dependency:go-offline || true
COPY src ./src
RUN mvn -B -q -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/target/explainer-service-0.1.0.jar app.jar
RUN useradd --system --no-create-home explainer
USER explainer
EXPOSE 8081
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
