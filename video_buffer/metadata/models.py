from django.db import models

class Metadata(models.Model):
    """
    Represents general metadata information.
    
    Attributes:
        - primary_key (CharField): The primary key column name.
        - description (TextField): Optional description for the metadata.
    """
    primary_key = models.CharField(max_length=255, help_text="The column name used as the primary key.")
    description = models.TextField(blank=True, null=True, help_text="Optional description of the metadata.")

    class Meta:
        db_table = 'metadata'
        verbose_name_plural = 'Metadata'

    def __str__(self):
        return f"Metadata with primary key: {self.primary_key}"
    
class Language(models.Model):
    """
    Model to define and manage supported languages.
    """
    code = models.CharField(max_length=10, unique=True)  # ISO 639-1 language codes, e.g., 'en', 'fr'
    name = models.CharField(max_length=50)  # e.g., 'English', 'French'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'language'
        verbose_name_plural = 'Languages'

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class MetadataColumn(models.Model):
    """
    Represents a metadata column.
    
    Attributes:
        - metadata (ForeignKey): A reference to the Metadata object.
        - column_name (CharField): The internal name of the column.
        - type (CharField): The data type of the column (e.g., "string").
        - is_required (BooleanField): Whether the column is required.
        - is_active (BooleanField): Whether the column is currently active.
    """
    metadata = models.ForeignKey(
        Metadata, 
        on_delete=models.CASCADE, 
        related_name='columns',
        help_text="The metadata this column belongs to."
    )
    column_name = models.CharField(max_length=255, help_text="The internal name of the column.")
    type = models.CharField(max_length=50, help_text="The data type of the column (e.g., 'string').")
    is_required = models.BooleanField(default=False, help_text="Indicates if this column is required.")
    is_active = models.BooleanField(default=True, help_text="Indicates if this column is currently active.")

    class Meta:
        db_table = 'metadata_column'
        verbose_name_plural = 'Metadata Columns'
        unique_together = ('metadata', 'column_name')  # Ensure unique columns per metadata entry
        indexes = [
            models.Index(fields=['metadata', 'column_name']),
        ]

    def __str__(self):
        return f"Column: {self.column_name} (Type: {self.type}, Required: {self.is_required})"

class MetadataLocalization(models.Model):
    """
    Represents localized metadata for columns.
    
    Attributes:
        - metadata_column (ForeignKey): A reference to the MetadataColumn object.
        - language (CharField): The language code (e.g., "en", "de").
        - title (CharField): Localized title of the column.
        - description (TextField): Localized description of the column.
    """
    metadata_column = models.ForeignKey(
        MetadataColumn, 
        on_delete=models.CASCADE, 
        related_name='localizations', 
        help_text="The metadata column being localized."
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, help_text="Localized title of the column.")
    description = models.TextField(blank=True, null=True, help_text="Localized description of the column.")

    class Meta:
        db_table = 'metadata_localization'
        verbose_name_plural = 'Metadata Localizations'
        unique_together = ('metadata_column', 'language')  # Ensure unique localization per column-language pair
        indexes = [
            models.Index(fields=['metadata_column', 'language']),
        ]

    def __str__(self):
        return f"Localization for '{self.metadata_column.column_name}' in {self.language}"

class Filter(models.Model):
    """
    Represents filters used to filter the metadata events.
    
    Attributes:
        - filter_name (CharField): The internal name of the filter.
        - title (CharField): The display name of the filter.
        - type (CharField): The data type of the filter (e.g., "enum").
        - is_active (BooleanField): Whether the filter is currently active.
    """
    filter_name = models.CharField(max_length=255, help_text="The internal name of the filter.")
    type = models.CharField(max_length=50, help_text="The data type of the filter (e.g., 'enum').")
    is_active = models.BooleanField(default=True, help_text="Indicates if the filter is currently active.")

    class Meta:
        db_table = 'filter'
        verbose_name_plural = 'Filters'
        unique_together = ('filter_name',)
        indexes = [
            models.Index(fields=['filter_name']),
        ]

    def __str__(self):
        return f"Filter: {self.filter_name} (Type: {self.type})"


class FilterItem(models.Model):
    """
    Represents filter items (e.g., individual options for a filter).
    
    Attributes:
        - filter (ForeignKey): A reference to the Filter object.
        - item_key (CharField): The internal key of the filter item (e.g., "impurity").
        - item_value (CharField): The display value of the filter item (e.g., "Störstoff").
        - is_active (BooleanField): Whether the filter item is currently active.
    """
    filter = models.ForeignKey(Filter, on_delete=models.CASCADE, related_name='items')
    item_key = models.CharField(max_length=255, help_text="The internal key for the filter item (e.g., 'impurity').")
    is_active = models.BooleanField(default=True, help_text="Indicates if the filter item is currently active.")

    class Meta:
        db_table = 'filter_item'
        verbose_name_plural = 'Filter Items'
        unique_together = ('filter', 'item_key')  # Ensure unique filter items per filter
        indexes = [
            models.Index(fields=['filter', 'item_key']),
        ]

    def __str__(self):
        return f"Filter Item: {self.item_key} (Key: {self.item_key})"
    
class FilterLocalization(models.Model):
    """
    Represents localized metadata for filters.
    
    Attributes:
        - filter (ForeignKey): A reference to the Filter object.
        - language (CharField): The language code (e.g., "en", "de").
        - title (CharField): Localized title of the filter.
        - description (TextField): Localized description of the filter.
    """
    filter = models.ForeignKey(
        'Filter', 
        on_delete=models.CASCADE, 
        related_name='localizations', 
        help_text="The filter being localized."
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, help_text="Localized title of the filter.")
    description = models.TextField(blank=True, null=True, help_text="Localized description of the filter.")

    class Meta:
        db_table = 'filter_localization'
        verbose_name_plural = 'Filter Localizations'
        unique_together = ('filter', 'language')  # Ensure unique localization per filter-language pair
        indexes = [
            models.Index(fields=['filter', 'language']),
        ]

    def __str__(self):
        return f"Filter Localization for '{self.title}' in {self.language}"


class FilterItemLocalization(models.Model):
    """
    Represents localized metadata for filter items.
    
    Attributes:
        - filter_item (ForeignKey): A reference to the FilterItem object.
        - language (CharField): The language code (e.g., "en", "de").
        - item_value (CharField): Localized value of the filter item.
    """
    filter_item = models.ForeignKey(
        'FilterItem', 
        on_delete=models.CASCADE, 
        related_name='localizations', 
        help_text="The filter item being localized."
    )
    language = models.CharField(max_length=10, help_text="ISO 639-1 language code, e.g., 'en', 'de'.")
    item_value = models.CharField(max_length=255, help_text="Localized value of the filter item.")

    class Meta:
        db_table = 'filter_item_localization'
        verbose_name_plural = 'Filter Item Localizations'
        unique_together = ('filter_item', 'language')  # Ensure unique localization per filter item-language pair
        indexes = [
            models.Index(fields=['filter_item', 'language']),
        ]

    def __str__(self):
        return f"Filter Item Localization for '{self.filter_item.item_key}' in {self.language}"