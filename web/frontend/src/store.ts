import { create } from "zustand";

export type PipelineStage =
  | "idle"
  | "scraping"
  | "processing_images"
  | "generating_copy"
  | "review"
  | "publishing"
  | "done";

export interface ProcessedImage {
  public_url: string;
  score: number;
  selected: boolean;
}

export interface ListingData {
  url: string;
  listing_id: string;
  title: string | null;
  price: string | null;
  address: string | null;
  description: string | null;
  images: string[];
  attributes: Record<string, string>;
}

interface PipelineState {
  stage: PipelineStage;
  progress: string;
  error: string | null;
  listing: ListingData | null;
  images: ProcessedImage[];
  storyUrl: string | null;
  facebookCopy: string;
  instagramCopy: string;
  publishResults: Record<string, unknown>;

  setStage: (stage: PipelineStage) => void;
  setProgress: (msg: string) => void;
  setError: (err: string | null) => void;
  setListing: (data: ListingData) => void;
  setImages: (imgs: ProcessedImage[]) => void;
  setStoryUrl: (url: string | null) => void;
  toggleImage: (index: number) => void;
  reorderImages: (reordered: ProcessedImage[]) => void;
  setFacebookCopy: (copy: string) => void;
  setInstagramCopy: (copy: string) => void;
  setPublishResults: (results: Record<string, unknown>) => void;
  reset: () => void;
}

const INITIAL = {
  stage: "idle" as PipelineStage,
  progress: "",
  error: null,
  listing: null,
  images: [],
  storyUrl: null,
  facebookCopy: "",
  instagramCopy: "",
  publishResults: {},
};

export const useStore = create<PipelineState>((set) => ({
  ...INITIAL,
  setStage: (stage) => set({ stage, error: null }),
  setProgress: (progress) => set({ progress }),
  setError: (error) => set({ error }),
  setListing: (listing) => set({ listing }),
  setImages: (images) => set({ images }),
  setStoryUrl: (storyUrl) => set({ storyUrl }),
  toggleImage: (index) =>
    set((s) => {
      const img = s.images[index];
      if (!img.selected && s.images.filter((i) => i.selected).length >= 10) return s;
      return {
        images: s.images.map((im, i) =>
          i === index ? { ...im, selected: !im.selected } : im,
        ),
      };
    }),
  reorderImages: (reordered) => set({ images: reordered }),
  setFacebookCopy: (facebookCopy) => set({ facebookCopy }),
  setInstagramCopy: (instagramCopy) => set({ instagramCopy }),
  setPublishResults: (publishResults) => set({ publishResults }),
  reset: () => set(INITIAL),
}));
