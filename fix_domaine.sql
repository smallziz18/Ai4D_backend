-- Script SQL pour créer les colonnes domaine
-- À exécuter avec: psql -U user -d dbname -f fix_domaine.sql

-- 1. Nettoyer l'état Alembic
DELETE FROM alembic_version WHERE version_num LIKE '%domaine%' OR version_num = 'add_domaine_field';

-- 2. Supprimer les colonnes existantes
ALTER TABLE etudiant DROP COLUMN IF EXISTS domaine CASCADE;
ALTER TABLE professeur DROP COLUMN IF EXISTS domaine CASCADE;

-- 3. Supprimer l'ancien type enum
DROP TYPE IF EXISTS domaine CASCADE;

-- 4. Créer le type enum avec les valeurs correctes
CREATE TYPE domaine AS ENUM (
    'Informatique',
    'Data Science',
    'Droit',
    'Marketing',
    'Chimie',
    'Physique',
    'Médecine',
    'Biologie',
    'Économie',
    'Management',
    'Général'
);

-- 5. Ajouter les colonnes
ALTER TABLE etudiant ADD COLUMN domaine domaine NOT NULL DEFAULT 'Général';
ALTER TABLE professeur ADD COLUMN domaine domaine NOT NULL DEFAULT 'Général';

-- 6. Vérifier
SELECT 'Domaine ENUM créé avec les valeurs:' AS info;
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'domaine'::regtype ORDER BY enumsortorder;

SELECT 'Colonnes créées:' AS info;
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE column_name = 'domaine' AND table_schema = 'public';

