import { describe, it, expect } from "vitest";
import {
  getLanguagesForTier,
  getWhisperCode,
  getFallbackLanguage,
  type PricingTierType,
} from "../languages";

describe("Languages Utilities", () => {
  describe("getLanguagesForTier", () => {
    it("returns common languages for budget tier", () => {
      const languages = getLanguagesForTier("budget");

      expect(languages.length).toBeGreaterThan(0);
      // Budget tier should have core languages
      expect(languages.some((l) => l.code === "en-US")).toBe(true);
      expect(languages.some((l) => l.code === "es-ES")).toBe(true);
      expect(languages.some((l) => l.code === "fr-FR")).toBe(true);
      expect(languages.some((l) => l.code === "de-DE")).toBe(true);
      expect(languages.some((l) => l.code === "ja-JP")).toBe(true);
    });

    it("returns more languages for balanced tier than budget", () => {
      const budgetLanguages = getLanguagesForTier("budget");
      const balancedLanguages = getLanguagesForTier("balanced");

      expect(balancedLanguages.length).toBeGreaterThanOrEqual(budgetLanguages.length);
      // Balanced should include additional Google-supported languages
      expect(balancedLanguages.some((l) => l.code === "ar-SA")).toBe(true);
      expect(balancedLanguages.some((l) => l.code === "he-IL")).toBe(true);
    });

    it("returns most languages for premium tier", () => {
      const balancedLanguages = getLanguagesForTier("balanced");
      const premiumLanguages = getLanguagesForTier("premium");

      expect(premiumLanguages.length).toBeGreaterThanOrEqual(balancedLanguages.length);
      // Premium should have additional Whisper-supported languages
      expect(premiumLanguages.some((l) => l.code === "ur-PK")).toBe(true);
      expect(premiumLanguages.some((l) => l.code === "ne-NP")).toBe(true);
    });

    it("returns same languages for premium and premium-mini tiers", () => {
      const premiumLanguages = getLanguagesForTier("premium");
      const premiumMiniLanguages = getLanguagesForTier("premium-mini");

      expect(premiumLanguages.length).toBe(premiumMiniLanguages.length);
      expect(premiumLanguages).toEqual(premiumMiniLanguages);
    });

    it("returns sorted languages alphabetically by name", () => {
      const languages = getLanguagesForTier("budget");

      for (let i = 1; i < languages.length; i++) {
        expect(languages[i - 1].name.localeCompare(languages[i].name)).toBeLessThanOrEqual(0);
      }
    });

    it("includes whisperCode for all languages", () => {
      const languages = getLanguagesForTier("premium");

      languages.forEach((lang) => {
        expect(lang.whisperCode).toBeDefined();
        expect(typeof lang.whisperCode).toBe("string");
      });
    });

    it("has valid BCP-47 codes for all languages", () => {
      const languages = getLanguagesForTier("premium");

      languages.forEach((lang) => {
        // BCP-47 codes typically follow pattern: language-REGION
        expect(lang.code).toMatch(/^[a-z]{2}-[A-Z]{2}$/);
      });
    });

    it("returns common languages for unknown tier", () => {
      const languages = getLanguagesForTier("unknown" as PricingTierType);

      // Should return common languages as fallback
      expect(languages.length).toBeGreaterThan(0);
      expect(languages.some((l) => l.code === "en-US")).toBe(true);
    });
  });

  describe("getWhisperCode", () => {
    it("returns whisper code for en-US", () => {
      const code = getWhisperCode("en-US");
      expect(code).toBe("en");
    });

    it("returns whisper code for en-GB", () => {
      const code = getWhisperCode("en-GB");
      expect(code).toBe("en");
    });

    it("returns whisper code for es-ES", () => {
      const code = getWhisperCode("es-ES");
      expect(code).toBe("es");
    });

    it("returns whisper code for es-MX", () => {
      const code = getWhisperCode("es-MX");
      expect(code).toBe("es");
    });

    it("returns whisper code for zh-CN", () => {
      const code = getWhisperCode("zh-CN");
      expect(code).toBe("zh");
    });

    it("returns whisper code for zh-TW", () => {
      const code = getWhisperCode("zh-TW");
      expect(code).toBe("zh");
    });

    it("returns whisper code for ja-JP", () => {
      const code = getWhisperCode("ja-JP");
      expect(code).toBe("ja");
    });

    it("returns whisper code for premium languages", () => {
      expect(getWhisperCode("ar-SA")).toBe("ar");
      expect(getWhisperCode("he-IL")).toBe("he");
      expect(getWhisperCode("ur-PK")).toBe("ur");
    });

    it("returns undefined for unknown language code", () => {
      const code = getWhisperCode("xx-XX");
      expect(code).toBeUndefined();
    });

    it("returns undefined for empty string", () => {
      const code = getWhisperCode("");
      expect(code).toBeUndefined();
    });
  });

  describe("getFallbackLanguage", () => {
    it("returns same language if valid for tier", () => {
      const result = getFallbackLanguage("en-US", "budget");
      expect(result).toBe("en-US");
    });

    it("returns same language for common languages across all tiers", () => {
      expect(getFallbackLanguage("en-US", "budget")).toBe("en-US");
      expect(getFallbackLanguage("en-US", "balanced")).toBe("en-US");
      expect(getFallbackLanguage("en-US", "premium")).toBe("en-US");
    });

    it("returns en-US as fallback for invalid language in budget tier", () => {
      // Arabic is not available in budget tier (only balanced+)
      const result = getFallbackLanguage("ar-SA", "budget");
      expect(result).toBe("en-US");
    });

    it("returns same language when premium language used with premium tier", () => {
      const result = getFallbackLanguage("ar-SA", "premium");
      expect(result).toBe("ar-SA");
    });

    it("returns same language when balanced language used with balanced tier", () => {
      const result = getFallbackLanguage("ar-SA", "balanced");
      expect(result).toBe("ar-SA");
    });

    it("returns en-US for premium-only language on budget tier", () => {
      // Urdu is premium only
      const result = getFallbackLanguage("ur-PK", "budget");
      expect(result).toBe("en-US");
    });

    it("returns en-US for completely unknown language", () => {
      const result = getFallbackLanguage("xx-XX", "premium");
      expect(result).toBe("en-US");
    });

    it("returns en-US for empty language string", () => {
      const result = getFallbackLanguage("", "budget");
      expect(result).toBe("en-US");
    });

    it("handles tier change from premium to budget correctly", () => {
      // Arabic was available on premium, but not on budget
      const result = getFallbackLanguage("ar-SA", "budget");
      expect(result).toBe("en-US");
    });

    it("handles tier change from premium to balanced correctly", () => {
      // Some premium languages may not be available on balanced
      // Urdu (ur-PK) is premium only
      const result = getFallbackLanguage("ur-PK", "balanced");
      expect(result).toBe("en-US");
    });

    it("maintains language when upgrading tier", () => {
      // Common language should work across all tiers
      const lang = "fr-FR";
      expect(getFallbackLanguage(lang, "budget")).toBe(lang);
      expect(getFallbackLanguage(lang, "balanced")).toBe(lang);
      expect(getFallbackLanguage(lang, "premium")).toBe(lang);
    });
  });

  describe("Language Coverage", () => {
    it("budget tier has at least 30 languages", () => {
      const languages = getLanguagesForTier("budget");
      expect(languages.length).toBeGreaterThanOrEqual(30);
    });

    it("balanced tier has more than budget tier", () => {
      const budget = getLanguagesForTier("budget");
      const balanced = getLanguagesForTier("balanced");
      expect(balanced.length).toBeGreaterThan(budget.length);
    });

    it("premium tier has the most languages", () => {
      const balanced = getLanguagesForTier("balanced");
      const premium = getLanguagesForTier("premium");
      expect(premium.length).toBeGreaterThanOrEqual(balanced.length);
    });

    it("all tiers include English (US)", () => {
      const tiers: PricingTierType[] = ["budget", "balanced", "premium-mini", "premium"];

      tiers.forEach((tier) => {
        const languages = getLanguagesForTier(tier);
        expect(languages.some((l) => l.code === "en-US")).toBe(true);
      });
    });

    it("no duplicate language codes within a tier", () => {
      const tiers: PricingTierType[] = ["budget", "balanced", "premium-mini", "premium"];

      tiers.forEach((tier) => {
        const languages = getLanguagesForTier(tier);
        const codes = languages.map((l) => l.code);
        const uniqueCodes = new Set(codes);
        expect(uniqueCodes.size).toBe(codes.length);
      });
    });
  });
});
