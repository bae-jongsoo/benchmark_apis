from django.db import models

class Food(models.Model):
    food_code = models.CharField(max_length=20, unique=True)  # 식품코드
    food_name = models.CharField(max_length=200)               # 식품명
    data_type = models.CharField(max_length=50)                # 데이터구분명
    energy_kcal = models.FloatField(null=True, blank=True)     # 에너지(kcal)
    water_g = models.FloatField(null=True, blank=True)         # 수분(g)
    protein_g = models.FloatField(null=True, blank=True)       # 단백질(g)
    fat_g = models.FloatField(null=True, blank=True)           # 지방(g)
    carbohydrate_g = models.FloatField(null=True, blank=True)  # 탄수화물(g)
    sugar_g = models.FloatField(null=True, blank=True)         # 당류(g)
    fiber_g = models.FloatField(null=True, blank=True)         # 식이섬유(g)
    calcium_mg = models.FloatField(null=True, blank=True)      # 칼슘(mg)
    sodium_mg = models.FloatField(null=True, blank=True)       # 나트륨(mg)
    vitamin_c_mg = models.FloatField(null=True, blank=True)    # 비타민C(mg)
    source_name = models.CharField(max_length=200, null=True, blank=True)  # 출처명

    class Meta:
        db_table = "foods"
        indexes = [
            models.Index(fields=["data_type"]),
            models.Index(fields=["energy_kcal"]),
            models.Index(fields=["protein_g"]),
        ]

    def __str__(self):
        return f"{self.food_code} - {self.food_name}"
