package com.benchmark.dto;

import com.benchmark.entity.Food;
import com.fasterxml.jackson.annotation.JsonProperty;

public record FoodOut(
        @JsonProperty("food_code") String foodCode,
        @JsonProperty("food_name") String foodName,
        @JsonProperty("data_type") String dataType,
        @JsonProperty("energy_kcal") Double energyKcal,
        @JsonProperty("water_g") Double waterG,
        @JsonProperty("protein_g") Double proteinG,
        @JsonProperty("fat_g") Double fatG,
        @JsonProperty("carbohydrate_g") Double carbohydrateG,
        @JsonProperty("sugar_g") Double sugarG,
        @JsonProperty("fiber_g") Double fiberG,
        @JsonProperty("calcium_mg") Double calciumMg,
        @JsonProperty("sodium_mg") Double sodiumMg,
        @JsonProperty("vitamin_c_mg") Double vitaminCMg,
        @JsonProperty("source_name") String sourceName
) {
    public static FoodOut from(Food food) {
        return new FoodOut(
                food.getFoodCode(), food.getFoodName(), food.getDataType(),
                food.getEnergyKcal(), food.getWaterG(), food.getProteinG(),
                food.getFatG(), food.getCarbohydrateG(), food.getSugarG(),
                food.getFiberG(), food.getCalciumMg(), food.getSodiumMg(),
                food.getVitaminCMg(), food.getSourceName()
        );
    }
}
