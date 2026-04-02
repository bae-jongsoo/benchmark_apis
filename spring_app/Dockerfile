FROM eclipse-temurin:21-jdk AS build

WORKDIR /app
COPY spring_app/ .

RUN chmod +x gradlew 2>/dev/null || true
# Use gradle wrapper if exists, otherwise install gradle
RUN if [ -f gradlew ]; then \
        ./gradlew bootJar --no-daemon; \
    else \
        apt-get update && apt-get install -y wget unzip && \
        wget -q https://services.gradle.org/distributions/gradle-8.13-bin.zip && \
        unzip -q gradle-8.13-bin.zip && \
        ./gradle-8.13/bin/gradle bootJar --no-daemon; \
    fi

FROM eclipse-temurin:21-jre

WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar

CMD java \
    -Dserver.tomcat.threads.max=${TOMCAT_MAX_THREADS:-200} \
    -jar app.jar
