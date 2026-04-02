package com.benchmark.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "foods")
public class Food {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "food_code", length = 20, unique = true, nullable = false)
    private String foodCode;

    @Column(name = "food_name", length = 200, nullable = false)
    private String foodName;

    @Column(name = "data_type", length = 50, nullable = false)
    private String dataType;

    @Column(name = "energy_kcal")
    private Double energyKcal;

    @Column(name = "water_g")
    private Double waterG;

    @Column(name = "protein_g")
    private Double proteinG;

    @Column(name = "fat_g")
    private Double fatG;

    @Column(name = "carbohydrate_g")
    private Double carbohydrateG;

    @Column(name = "sugar_g")
    private Double sugarG;

    @Column(name = "fiber_g")
    private Double fiberG;

    @Column(name = "calcium_mg")
    private Double calciumMg;

    @Column(name = "sodium_mg")
    private Double sodiumMg;

    @Column(name = "vitamin_c_mg")
    private Double vitaminCMg;

    @Column(name = "source_name", length = 200)
    private String sourceName;

    // Getters
    public Long getId() { return id; }
    public String getFoodCode() { return foodCode; }
    public String getFoodName() { return foodName; }
    public String getDataType() { return dataType; }
    public Double getEnergyKcal() { return energyKcal; }
    public Double getWaterG() { return waterG; }
    public Double getProteinG() { return proteinG; }
    public Double getFatG() { return fatG; }
    public Double getCarbohydrateG() { return carbohydrateG; }
    public Double getSugarG() { return sugarG; }
    public Double getFiberG() { return fiberG; }
    public Double getCalciumMg() { return calciumMg; }
    public Double getSodiumMg() { return sodiumMg; }
    public Double getVitaminCMg() { return vitaminCMg; }
    public String getSourceName() { return sourceName; }
}
