package com.benchmark.controller;

import com.benchmark.dto.FoodListResponse;
import com.benchmark.dto.FoodOut;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/benchmark")
public class BenchmarkController {

    private static final List<FoodOut> DUMMY_FOODS;

    static {
        DUMMY_FOODS = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            DUMMY_FOODS.add(new FoodOut(
                    String.format("D%05d", i), "테스트식품" + i,
                    "일반", 100.0 + i, 80.0,
                    10.0, 5.0, 20.0,
                    3.0, 2.0, 50.0,
                    200.0, 10.0, "테스트"
            ));
        }
    }

    private int fib(int n) {
        if (n <= 1) return n;
        return fib(n - 1) + fib(n - 2);
    }

    @GetMapping("/cpu")
    public Map<String, Object> cpuBound() {
        int result = fib(25);
        return Map.of("result", result);
    }

    @GetMapping("/io")
    public Map<String, Object> ioBound() throws InterruptedException {
        Thread.sleep(100);
        return Map.of("result", "ok", "slept_ms", 100);
    }

    @GetMapping("/mixed")
    public Map<String, Object> mixed() throws InterruptedException {
        int result = fib(25);
        Thread.sleep(50);
        return Map.of("result", result, "slept_ms", 50);
    }

    @GetMapping("/fake-io")
    public FoodListResponse fakeIo() throws InterruptedException {
        Thread.sleep(5);
        return new FoodListResponse(DUMMY_FOODS, 1000, 1, 20);
    }
}
