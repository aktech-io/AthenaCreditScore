package com.athena.userservice.aspect;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Arrays;

@Aspect
@Component
@Slf4j
public class LoggingAspect {

    @Pointcut("within(@org.springframework.web.bind.annotation.RestController *)")
    public void controllerMethods() {}

    @Around("controllerMethods()")
    public Object logAround(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();

        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = attrs != null ? attrs.getRequest() : null;

        String method = joinPoint.getSignature().getName();
        String className = joinPoint.getTarget().getClass().getSimpleName();
        String uri = request != null ? request.getRequestURI() : "UNKNOWN";
        String httpMethod = request != null ? request.getMethod() : "UNKNOWN";
        String user = request != null && request.getUserPrincipal() != null
                ? request.getUserPrincipal().getName() : "ANONYMOUS";

        log.info(">> [{}] {} {} | {}.{}", user, httpMethod, uri, className, method);

        try {
            Object result = joinPoint.proceed();
            long duration = System.currentTimeMillis() - start;
            String status = result instanceof org.springframework.http.ResponseEntity
                    ? ((org.springframework.http.ResponseEntity<?>) result).getStatusCode().toString() : "OK";
            log.info("<< [{}] {} {}ms", user, status, duration);
            return result;
        } catch (Throwable e) {
            long duration = System.currentTimeMillis() - start;
            log.error("!! [{}] {} {}ms | {}", user, method, duration, e.getMessage());
            throw e;
        }
    }
}
