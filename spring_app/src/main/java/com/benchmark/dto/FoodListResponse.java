package com.benchmark.dto;

import java.util.List;

public record FoodListResponse(
        List<FoodOut> items,
        long total,
        int page,
        int size
) {}
