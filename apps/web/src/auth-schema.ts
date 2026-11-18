import {z} from 'zod';

// Keep client bounds aligned with the authoritative FastAPI credential schema.
export const authSchema = z.object({
  email: z.string().max(254, 'Use an email address of at most 254 characters').email(),
  password: z.string().min(12, 'Use at least 12 characters').max(128, 'Use at most 128 characters'),
});

export type AuthValues = z.infer<typeof authSchema>;
