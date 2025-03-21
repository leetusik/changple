# Admin Panel Foreign Key Constraint Fix

## Issue
The Django admin panel was experiencing foreign key constraint failures when trying to edit any models, including users and PostStatus objects. This was happening because:

1. The project uses a custom user model (`users.User`)
2. The Django admin log table (`django_admin_log`) still had a foreign key constraint to the default `auth_user` table
3. This mismatch caused all admin panel edits to fail with:
```
IntegrityError: FOREIGN KEY constraint failed
```

## Solution
Created and executed a fix script (`fix_admin_log.py`) that:
1. Temporarily disabled foreign key constraints
2. Backed up existing admin log entries
3. Recreated the admin log table with correct foreign key reference to `users_user`
4. Restored valid log entries
5. Re-enabled foreign key constraints

### Fix Script Details
```python
# Key parts of the fix:
CREATE TABLE "django_admin_log" (
    ...
    "user_id" integer NOT NULL REFERENCES "users_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    ...
)
```

## Management Commands
Several Django management commands were created to help manage users and fix issues:

### Active Commands
1. `create_admin_user`
   - Custom version of createsuperuser that properly sets user_type to 'admin'
   - Usage: `python manage.py create_admin_user`

2. `update_superusers`
   - Updates existing superusers to have admin user_type
   - Usage: `python manage.py update_superusers`

3. `fix_social_auth_user`
   - Safely updates social user data without violating constraints
   - Usage: `python manage.py fix_social_auth_user <user_id> [--field value]`
   - Example: `python manage.py fix_social_auth_user 6 --name "New Name" --is_premium True`

### Removed Commands
The following commands were removed as they were no longer needed or potentially dangerous:
- `set_random_passwords.py` - One-time setup script
- `delete_social_users.py` - Dangerous cleanup script

## Cleanup
After fixing the admin panel:
1. Removed unnecessary auth_user references
2. Ensured proper foreign key constraints
3. Verified admin panel functionality for all models
4. Cleaned up unnecessary management commands
5. Removed Python cache files

## Testing
The fix was successful, and the admin panel now allows:
- Editing user profiles
- Modifying PostStatus entries
- Managing all other models
- Proper logging of admin actions

## Future Considerations
When making changes to the user model or other core Django components:
1. Always check foreign key constraints
2. Update any dependent tables
3. Consider impact on Django's built-in functionality like admin logging
4. Keep only necessary management commands
5. Document command usage and purpose

## Related Files
- `users/models.py`: Custom user model implementation
- `users/admin.py`: Custom admin panel configuration
- `users/management/commands/create_admin_user.py`: Custom admin user creation
- `users/management/commands/update_superusers.py`: Superuser type fix
- `users/management/commands/fix_social_auth_user.py`: Social user management 