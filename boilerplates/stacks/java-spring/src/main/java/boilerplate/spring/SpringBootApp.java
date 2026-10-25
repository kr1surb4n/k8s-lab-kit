package boilerplate.spring;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.info.BuildProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.InetAddress;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@SpringBootApplication
public class SpringBootApp {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootApp.class, args);
    }
}

@RestController
class HealthController {

    private final BuildProperties buildProperties;

    public HealthController(Optional<BuildProperties> buildProperties) {
        this.buildProperties = buildProperties.orElse(null);
    }

    @GetMapping("/healthz")
    public Map<String, Object> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "ok");
        response.put("app", "java-spring");
        response.put("version", buildProperties != null ? buildProperties.getVersion() : "1.0.0");
        response.put("hostname", getHostname());
        return response;
    }

    @GetMapping("/ready")
    public Map<String, String> ready() {
        return Map.of("status", "ready", "app", "java-spring");
    }

    @GetMapping("/api/hello")
    public Map<String, Object> hello() {
        Map<String, Object> response = new HashMap<>();
        response.put("message", "Hello from java-spring");
        response.put("version", buildProperties != null ? buildProperties.getVersion() : "1.0.0");
        response.put("hostname", getHostname());
        return response;
    }

    private String getHostname() {
        try {
            return InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            return "unknown";
        }
    }
}

@Configuration
class ActuatorConfig {
    @Bean
    public BuildProperties buildProperties() {
        return new BuildProperties() {
            @Override
            public String getName() { return "java-spring"; }
            @Override
            public String getVersion() { return "1.0.0"; }
            @Override
            public String getGroup() { return "boilerplate"; }
            @Override
            public String getArtifact() { return "java-spring"; }
        };
    }
}