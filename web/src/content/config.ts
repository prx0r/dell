// src/content/config.ts — Blog content schema
import { defineCollection, z } from 'astro:content';

export const blogCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.date(),
    updatedDate: z.date().optional(),
    author: z.string().default('Dell Team'),
    tags: z.array(z.string()).default([]),
    image: z.string().optional(),
  }),
});

export const collections = {
  blog: blogCollection,
};