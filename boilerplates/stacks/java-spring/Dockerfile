# Java/Spring Boot boilerplate — minimal production image.
#
# Build: docker build -t boilerplate/java-spring:1.0 boilerplates/stacks/java-spring
# Run:   docker run -p 8080:8080 boilerplate/java-spring:1.0
#
# Multi-stage: build with Maven, copy fat jar to final JRE image.
FROM maven:3.9-eclipse-temurin-21-alpine AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn -B package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
# Non-root user
RUN addgroup -g 1001 -S spring && adduser -S -u 1001 -G spring spring
COPY --from=builder --chown=spring:spring /app/target/*.jar /app/app.jar
USER spring
EXPOSE 8080
ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -Djava.security.egd=file:/dev/./urandom"
# Startup probe needs longer initial delay for Spring Boot startup
HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]