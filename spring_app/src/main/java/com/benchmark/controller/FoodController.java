package com.benchmark.controller;

import com.benchmark.dto.FoodListResponse;
import com.benchmark.dto.FoodOut;
import com.benchmark.entity.Food;
import com.benchmark.repository.FoodRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api")
public class FoodController {

    private final FoodRepository foodRepository;

    private static final Map<String, Sort> SORT_MAP = Map.ofEntries(
            Map.entry("food_name", Sort.by(Sort.Direction.ASC, "foodName")),
            Map.entry("-food_name", Sort.by(Sort.Direction.DESC, "foodName")),
            Map.entry("energy_kcal", Sort.by(Sort.Direction.ASC, "energyKcal")),
            Map.entry("-energy_kcal", Sort.by(Sort.Direction.DESC, "energyKcal")),
            Map.entry("protein_g", Sort.by(Sort.Direction.ASC, "proteinG")),
            Map.entry("-protein_g", Sort.by(Sort.Direction.DESC, "proteinG")),
            Map.entry("fat_g", Sort.by(Sort.Direction.ASC, "fatG")),
            Map.entry("-fat_g", Sort.by(Sort.Direction.DESC, "fatG")),
            Map.entry("carbohydrate_g", Sort.by(Sort.Direction.ASC, "carbohydrateG")),
            Map.entry("-carbohydrate_g", Sort.by(Sort.Direction.DESC, "carbohydrateG"))
    );

    public FoodController(FoodRepository foodRepository) {
        this.foodRepository = foodRepository;
    }

    @GetMapping("/foods")
    public FoodListResponse foodList(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false, name = "data_type") String dataType
    ) {
        PageRequest pageRequest = PageRequest.of(page - 1, size);
        Page<Food> result;

        if (dataType != null && !dataType.isEmpty()) {
            result = foodRepository.findByDataType(dataType, pageRequest);
        } else {
            result = foodRepository.findAll(pageRequest);
        }

        return new FoodListResponse(
                result.getContent().stream().map(FoodOut::from).toList(),
                result.getTotalElements(),
                page,
                size
        );
    }

    @GetMapping("/foods/search")
    public FoodListResponse foodSearch(
            @RequestParam(required = false, name = "min_energy") Double minEnergy,
            @RequestParam(required = false, name = "max_energy") Double maxEnergy,
            @RequestParam(required = false, name = "data_type") String dataType,
            @RequestParam(defaultValue = "food_name") String sort,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        Specification<Food> spec = Specification.where(null);

        if (minEnergy != null) {
            spec = spec.and((root, query, cb) -> cb.greaterThanOrEqualTo(root.get("energyKcal"), minEnergy));
        }
        if (maxEnergy != null) {
            spec = spec.and((root, query, cb) -> cb.lessThanOrEqualTo(root.get("energyKcal"), maxEnergy));
        }
        if (dataType != null && !dataType.isEmpty()) {
            spec = spec.and((root, query, cb) -> cb.equal(root.get("dataType"), dataType));
        }

        Sort sortOrder = SORT_MAP.getOrDefault(sort, Sort.by(Sort.Direction.ASC, "foodName"));
        PageRequest pageRequest = PageRequest.of(page - 1, size, sortOrder);

        Page<Food> result = foodRepository.findAll(spec, pageRequest);

        return new FoodListResponse(
                result.getContent().stream().map(FoodOut::from).toList(),
                result.getTotalElements(),
                page,
                size
        );
    }
}
